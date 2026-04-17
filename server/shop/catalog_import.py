"""
Імпорт товарів з Google Таблиць (спільна логіка для Celery, HTTP, manage.py).

Не імпортуйте з management.commands — у частини середовищ це дає ModuleNotFoundError.
"""
from __future__ import annotations

import logging
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from shop.catalog_sheet_sources import iter_catalog_import_jobs
from shop.models import Catalog, Product, ProductProperty

_SERVER_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE") or str(_SERVER_ROOT / "credentials.json")
_sync_logger = logging.getLogger(__name__)


def _normalize_price(raw) -> Decimal | None:
    """Ціна з таблиці: '1 299 грн', '1299,50', '1299.5' → Decimal."""
    if raw is None:
        return None
    s = str(raw).strip().replace("\xa0", " ")
    s = re.sub(r"[^\d.,\-]", "", s.replace(" ", ""))
    if not s:
        return None
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = parts[0] + "." + parts[1]
        else:
            s = ",".join(parts).replace(",", "")
    else:
        s = s.replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        try:
            return Decimal(str(float(s)))
        except (ValueError, InvalidOperation):
            return None


def _is_likely_header_row(row, fields) -> bool:
    """Перший рядок таблиці часто містить «Артикул» замість реального SKU — пропускаємо."""
    if fields["article"] >= len(row):
        return False
    art = str(row[fields["article"]]).strip().lower()
    if not art:
        return False
    if art in ("артикул", "article", "код", "арт.", "id", "№", "код товару"):
        return True
    if "артикул" in art and len(art) < 32 and not any(ch.isdigit() for ch in art):
        return True
    return False


def _photo_cell_usable(cell) -> bool:
    """Таблиці часто дають http, формули без 'https' або лише id — старий 'https' у рядку відсіював усе."""
    if cell is None:
        return False
    s = str(cell).strip()
    if not s:
        return False
    low = s.lower()
    if "drive.google" in low and ("/d/" in s or "open?id=" in low or "id=" in low):
        return True
    if "http://" in low or "https://" in low:
        return True
    return False


def _drive_file_id(link: str) -> str | None:
    try:
        s = (link or "").strip()
        if "/d/" in s:
            return s.split("/d/", 1)[1].split("/")[0].split("?")[0]
        if "open?id=" in s:
            return s.split("open?id=", 1)[1].split("&")[0]
        if "id=" in s and "drive.google" in s.lower():
            return s.split("id=", 1)[1].split("&")[0]
    except (IndexError, AttributeError):
        pass
    return None


def _sizes_from_row(row, fields):
    """Розміри з таблиці; якщо немає у whitelist valid_size — беремо значення з комірки (одяг з нестандартними мітками)."""
    sizes: list = []
    if fields.get("size") is None:
        return sizes
    if fields["size"] >= len(row) or not str(row[fields["size"]]).strip():
        return sizes
    row_sizes = split_sizes(row[fields["size"]])
    sizes = valid_size(row_sizes)
    if len(sizes) == 0 and row_sizes:
        sizes = [x for x in row_sizes if x][:24]
    return sizes


def _merge_product_property(product: Product, title: str) -> ProductProperty:
    """
    Один запис ProductProperty на пару (product, title).
    Якщо в БД вже є дублікати (стара помилка імпорту) — лишаємо найменший pk, решту видаляємо.
    """
    qs = ProductProperty.objects.filter(title=title, product=product).order_by("pk")
    prop = qs.first()
    if prop is None:
        return ProductProperty.objects.create(title=title, product=product, active=True)
    dup_pks = list(qs.exclude(pk=prop.pk).values_list("pk", flat=True))
    if dup_pks:
        ProductProperty.objects.filter(pk__in=dup_pks).delete()
        _sync_logger.warning(
            "removed duplicate ProductProperty product_id=%s title=%s kept_pk=%s",
            product.pk,
            title,
            prop.pk,
        )
    return prop


def run_product_sync(log=print):
    """
    Імпорт/оновлення товарів з Google Таблиць (логіка спільна з manage.py update_products).
    log: callable(str) — для виводу прогресу (наприклад self.stdout.write у команді).
    """
    for catalog_title, spreadsheet_id, fields in iter_catalog_import_jobs():
        range_name = fields["sheet"]
        if not isinstance(range_name, list):
            range_name = [range_name]

        log(
            f"--- Каталог «{catalog_title}» · spreadsheet={spreadsheet_id} · sheet index(es)={range_name} ---"
        )
        try:
            rows = get_catalog_data(spreadsheet_id, range_name)
        except Exception as exc:
            log(f"ПОМИЛКА читання таблиці (пропускаємо цей блок): {exc}")
            _sync_logger.exception(
                "sync: get_catalog_data failed catalog=%s spreadsheet=%s",
                catalog_title,
                spreadsheet_id,
            )
            continue

        if len(rows) == 0:
            log("Таблиця порожня або діапазон не знайдено.")
            continue

        ind = 1
        for row in rows:
            log(f"{ind} / {len(rows)}")
            ind += 1
            if fields["article"] >= len(row) or row[fields["article"]] == "":
                continue
            if _is_likely_header_row(row, fields):
                continue

            try:
                if not Product.objects.filter(article=row[fields["article"]]).exists():
                    create_product(row, fields, catalog_title)
                else:
                    update_product(row, fields)
            except Exception as exc:
                log(
                    f"ПОМИЛКА рядка {ind - 1} (арт. {row[fields['article']] if fields['article'] < len(row) else '?'}): {exc}"
                )
                _sync_logger.exception(
                    "sync: row failed catalog=%s article_index=%s",
                    catalog_title,
                    fields.get("article"),
                )

        log(f"--- Завершено блок: «{catalog_title}» / {spreadsheet_id} ---")


def get_catalog_data(SPREADSHEET_ID, RANGE_NAME):
    data = []
    for i in RANGE_NAME:
        res = get_google_sheet_data_by_index(SPREADSHEET_ID, i)
        data += res
    return data


def get_sheet_id_by_index(spreadsheet_id, sheet_index):
    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet.get("sheets", [])

    if sheet_index < 0 or sheet_index >= len(sheets):
        raise ValueError(f"Індекс аркуша {sheet_index} поза межами (0 - {len(sheets) - 1}).")

    return sheets[sheet_index]["properties"]["title"]


def get_google_sheet_data_by_index(spreadsheet_id, sheet_index, range_name=None):
    sheet_title = get_sheet_id_by_index(spreadsheet_id, sheet_index)

    full_range = sheet_title if not range_name else f"{sheet_title}!{range_name}"

    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)

    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=full_range).execute()
    values = result.get("values", [])

    return values


def update_product(row, fields):
    product = Product.objects.get(article=row[fields["article"]])

    if fields["title"] < len(row) and row[fields["title"]] != "":
        product.active = True
        product.save(update_fields=["active"])
        product.title = row[fields["title"]]
        product.save(update_fields=["title"])
    else:
        product.active = False
        product.save(update_fields=["active"])

    if fields["price"] < len(row):
        raw_p = row[fields["price"]]
        if str(raw_p).strip() != "":
            price_dec = _normalize_price(raw_p)
            if price_dec is not None:
                product.active = True
                product.save(update_fields=["active"])
                product.price = price_dec
                product.save(update_fields=["price"])
        else:
            product.active = False
            product.save(update_fields=["active"])
            return
    else:
        product.active = False
        product.save(update_fields=["active"])
        return

    if (fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] == "") or (
        fields.get("count") is not None and fields["count"] < len(row) and row[fields["count"]] == ""
    ):
        product.active = False
        product.save(update_fields=["active"])
        return
    elif fields.get("count") is not None and fields["count"] < len(row) and row[fields["count"]] != "" and product.active is False:
        product.active = True
        product.save(update_fields=["active"])
        return
    elif fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] != "" and product.active is False:
        product.active = True
        product.save(update_fields=["active"])
        return

    if fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] != "":
        sizes = _sizes_from_row(row, fields)

        if len(sizes) == 0 or (fields["price"] < len(row) and _normalize_price(row[fields["price"]]) is None):
            product.active = False
            product.save(update_fields=["active"])
            return

        if len(sizes) != 0:
            product.product_properties.all().update(active=False)
            for size in sizes:
                prop = _merge_product_property(product, size)
                prop.active = True
                prop.save(update_fields=["active"])

    if fields.get("count") is not None and fields["count"] < len(row):
        cnt = str(row[fields["count"]]).strip()
        if cnt:
            prop = _merge_product_property(product, cnt)
            prop.active = True
            prop.save(update_fields=["active"])

    if fields.get("description") is not None and fields["description"] < len(row):
        product.description = str(row[fields["description"]])
        product.save(update_fields=["description"])

    if fields["photo"] < len(row) and _photo_cell_usable(row[fields["photo"]]):
        ph = download_photo(row[fields["photo"]])
        if ph is not None:
            product.photo.save(f"{product.article}_main.jpg", ph, save=True)


def create_product(row, fields, catalog_title):
    """Створює товар за артикулом/назвою/ціною; фото — за можливості (Drive uc-лінк часто дає HTML замість файлу)."""
    if (fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] == "") or (
        fields.get("count") is not None and fields["count"] < len(row) and row[fields["count"]] == ""
    ):
        return

    sizes = _sizes_from_row(row, fields)
    if fields.get("size") is not None and fields["size"] < len(row) and str(row[fields["size"]]).strip() != "":
        if len(sizes) == 0:
            return

    if fields["title"] >= len(row) or not str(row[fields["title"]]).strip():
        return

    if fields["price"] >= len(row):
        return
    price_dec = _normalize_price(row[fields["price"]])
    if price_dec is None:
        return

    desc = ""
    if fields.get("description") is not None and fields["description"] < len(row):
        desc = str(row[fields["description"]])

    if Catalog.objects.filter(title=catalog_title).exists():
        catalog = Catalog.objects.get(title=catalog_title)
    else:
        catalog = Catalog.objects.create(title=catalog_title)

    product = Product.objects.create(
        title=str(row[fields["title"]]).strip(),
        article=str(row[fields["article"]]).strip(),
        price=price_dec,
        catalog=catalog,
        description=desc,
    )

    if fields["photo"] < len(row) and _photo_cell_usable(row[fields["photo"]]):
        photo = download_photo(row[fields["photo"]])
        if photo is not None:
            product.photo.save(f"{row[fields['article']]}_main.jpg", photo, save=True)
        else:
            _sync_logger.warning(
                "create_product: skipped photo (download failed) article=%s",
                row[fields["article"]],
            )

    for size in dict.fromkeys(sizes):
        _merge_product_property(product, size)

    if not sizes and fields.get("count") is not None and fields["count"] < len(row):
        cnt = str(row[fields["count"]]).strip()
        if cnt:
            _merge_product_property(product, cnt)


def valid_size(row_sizes):
    data = []

    for i in row_sizes:
        if i in {"28", "29", "30", "31", "32", "33", "34", "35", "36", "38", "39", "40", "41", "42", "43", "44", "45", "46"}:
            data.append(i)
        elif i in {"S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL", "7XL"}:
            data.append(i)

    return data


def normalize_size(size):
    return size.upper().strip()


def split_sizes(size_string):
    sizes = re.split(r"[,\s\-]+", size_string)
    return [normalize_size(size) for size in sizes if size.strip()]


def _bytes_look_like_image(data: bytes) -> bool:
    if not data or len(data) < 3:
        return False
    if data[:2] == b"\xff\xd8":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def download_photo(link):
    """Завантаження фото за посиланням Google Drive (пряме uc — не завжди працює для великих файлів)."""
    try:
        file_id = _drive_file_id(link)
        if not file_id:
            return None
        download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        response = requests.get(download_url, timeout=60)
        if response.status_code == 200:
            data = response.content
            if _bytes_look_like_image(data):
                return ContentFile(data)
            low = data[:8000].lower()
            if b"<!doctype html" in low or b"<html" in low:
                _sync_logger.warning(
                    "download_photo: HTML instead of image (Drive warning/scan) file_id=%s",
                    file_id,
                )
                return None
            return ContentFile(data)
        _sync_logger.warning("download_photo: HTTP %s file_id=%s", response.status_code, file_id)
        return None
    except Exception as e:
        _sync_logger.exception("download_photo failed link=%s: %s", link, e)
        return None


def get_google_sheet_data(spreadsheet_id, range_name):
    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)

    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get("values", [])

    return values
