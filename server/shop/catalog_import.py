"""
Імпорт товарів з Google Таблиць (спільна логіка для Celery, HTTP, manage.py).

Не імпортуйте з management.commands — у частини середовищ це дає ModuleNotFoundError.
"""
from __future__ import annotations

import io
import logging
import time
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from shop.catalog_sheet_sources import iter_catalog_import_jobs
from shop.models import Catalog, Product, ProductProperty
from shop.sync_telegram import (
    format_block_done,
    format_block_empty,
    format_block_start,
    format_sync_summary,
    notify_sheet_error,
    send_catalog_sync_message,
)

_SERVER_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE") or str(_SERVER_ROOT / "credentials.json")
_sync_logger = logging.getLogger(__name__)

# Типовий id файлу в Google Drive (лише символи, без слешів — якщо вставили id у комірку без URL)
_BARE_DRIVE_FILE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{27,100}$")

# Під час run_product_sync — лічильники для Telegram по поточному блоці каталогу
_sync_import_active = False
_sync_block: dict = {}


def _sync_import_set_active(value: bool) -> None:
    global _sync_import_active
    _sync_import_active = value


def _sync_block_reset(
    catalog_title: str, spreadsheet_id: str, sheet_indexes, row_count: int
) -> None:
    global _sync_block
    _sync_block = {
        "catalog_title": catalog_title,
        "spreadsheet_id": spreadsheet_id,
        "sheet_indexes": sheet_indexes,
        "row_count": row_count,
        "rows_ok": 0,
        "rows_err": 0,
        "photo_fail": 0,
        "photo_cell_unrecognized": 0,
        "photo_fail_samples": [],
        "err_samples": [],
    }


def _sync_block_row_ok() -> None:
    if not _sync_import_active:
        return
    _sync_block["rows_ok"] = int(_sync_block.get("rows_ok", 0)) + 1


def _sync_block_row_err(article: str, exc: BaseException) -> None:
    if not _sync_import_active:
        return
    _sync_block["rows_err"] = int(_sync_block.get("rows_err", 0)) + 1
    samples: list = _sync_block.setdefault("err_samples", [])
    if len(samples) < 8:
        samples.append(f"{article}: {exc!s}")


def sync_block_photo_fail(detail: str = "") -> None:
    """Викликати, коли в комірці було посилання на фото, а файл не завантажився."""
    if not _sync_import_active:
        return
    _sync_block["photo_fail"] = int(_sync_block.get("photo_fail", 0)) + 1
    if detail:
        samples: list = _sync_block.setdefault("photo_fail_samples", [])
        if len(samples) < 6:
            samples.append(detail[:450])


def sync_block_photo_cell_unrecognized() -> None:
    """У колонці фото щось є, але це не схоже на http(s) / Drive — імпорт фото пропущено."""
    if not _sync_import_active:
        return
    _sync_block["photo_cell_unrecognized"] = int(_sync_block.get("photo_cell_unrecognized", 0)) + 1


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


def _looks_like_bare_drive_file_id(s: str) -> bool:
    t = re.sub(r"\s+", "", (s or "").strip())
    if not _BARE_DRIVE_FILE_ID_RE.fullmatch(t):
        return False
    return any(c.isalpha() for c in t)


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
    if _looks_like_bare_drive_file_id(s):
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
        m = re.search(r"(?:\?|&)fileId=([a-zA-Z0-9_-]+)", s, re.I)
        if m:
            return m.group(1)
        if "/" not in s and "?" not in s and _looks_like_bare_drive_file_id(s):
            return re.sub(r"\s+", "", s.strip())
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
    t0 = time.monotonic()
    row_errors: list[str] = []
    sheet_errors: list[str] = []
    catalogs_completed = 0
    rows_processed = 0

    send_catalog_sync_message("🔄 Розпочато імпорт товарів з Google Таблиць…")
    _sync_import_set_active(True)
    try:
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
                err_line = f"{catalog_title} | {spreadsheet_id} | {exc!s}"
                sheet_errors.append(err_line)
                notify_sheet_error(catalog_title, spreadsheet_id, exc)
                continue

            if len(rows) == 0:
                log("Таблиця порожня або діапазон не знайдено.")
                send_catalog_sync_message(format_block_empty(catalog_title, spreadsheet_id))
                catalogs_completed += 1
                continue

            _sync_block_reset(catalog_title, spreadsheet_id, range_name, len(rows))
            send_catalog_sync_message(
                format_block_start(catalog_title, spreadsheet_id, range_name, len(rows))
            )

            ind = 1
            for row in rows:
                log(f"{ind} / {len(rows)}")
                ind += 1
                if fields["article"] >= len(row) or row[fields["article"]] == "":
                    continue
                if _is_likely_header_row(row, fields):
                    continue

                art = str(row[fields["article"]]).strip() if fields["article"] < len(row) else "?"
                try:
                    if not Product.objects.filter(article=row[fields["article"]]).exists():
                        create_product(row, fields, catalog_title)
                    else:
                        update_product(row, fields)
                    rows_processed += 1
                    _sync_block_row_ok()
                except Exception as exc:
                    log(
                        f"ПОМИЛКА рядка {ind - 1} (арт. {row[fields['article']] if fields['article'] < len(row) else '?'}): {exc}"
                    )
                    _sync_logger.exception(
                        "sync: row failed catalog=%s article_index=%s",
                        catalog_title,
                        fields.get("article"),
                    )
                    _sync_block_row_err(art, exc)
                    row_errors.append(f"{catalog_title} · арт. {art} · {exc!s}")
                    if len(row_errors) > 200:
                        row_errors.pop(0)

            catalogs_completed += 1
            log(f"--- Завершено блок: «{catalog_title}» / {spreadsheet_id} ---")
            send_catalog_sync_message(
                format_block_done(
                    catalog_title,
                    spreadsheet_id,
                    _sync_block.get("rows_ok", 0),
                    _sync_block.get("rows_err", 0),
                    _sync_block.get("photo_fail", 0),
                    list(_sync_block.get("err_samples") or []),
                    photo_cell_unrecognized=_sync_block.get("photo_cell_unrecognized", 0),
                    photo_fail_samples=list(_sync_block.get("photo_fail_samples") or []),
                )
            )
    finally:
        _sync_import_set_active(False)

    duration = time.monotonic() - t0
    summary = format_sync_summary(
        duration_sec=duration,
        catalogs_completed=catalogs_completed,
        total_rows_iterated=rows_processed,
        row_errors=row_errors,
        sheet_errors=sheet_errors,
    )
    send_catalog_sync_message(summary)


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

    if fields["photo"] < len(row):
        cell = row[fields["photo"]]
        raw = str(cell).strip() if cell is not None else ""
        if raw and not _photo_cell_usable(cell):
            sync_block_photo_cell_unrecognized()
        elif _photo_cell_usable(cell):
            ph, ph_err = download_photo(cell)
            if ph is not None:
                product.photo.save(f"{product.article}_main.jpg", ph, save=True)
            else:
                sync_block_photo_fail(f"{product.article}: {ph_err or 'невідома причина'}")


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

    if fields["photo"] < len(row):
        cell = row[fields["photo"]]
        raw = str(cell).strip() if cell is not None else ""
        if raw and not _photo_cell_usable(cell):
            sync_block_photo_cell_unrecognized()
        elif _photo_cell_usable(cell):
            photo, ph_err = download_photo(cell)
            if photo is not None:
                product.photo.save(f"{row[fields['article']]}_main.jpg", photo, save=True)
            else:
                _sync_logger.warning(
                    "create_product: skipped photo article=%s reason=%s",
                    row[fields["article"]],
                    ph_err,
                )
                sync_block_photo_fail(f"{row[fields['article']]}: {ph_err or 'невідома причина'}")

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


def _response_looks_like_html(data: bytes) -> bool:
    if not data or len(data) < 10:
        return False
    low = data[: min(8000, len(data))].lower()
    return b"<!doctype html" in low or b"<html" in low


def _download_photo_via_drive_api(file_id: str) -> tuple[bytes | None, str | None]:
    """
    Завантаження бінарного вмісту файлу через Drive API (service account).
    Потрібен доступ: файл або папка в Drive «поділені» з client_email з credentials.json.
    """
    if not os.path.isfile(CREDENTIALS_FILE):
        msg = f"немає credentials за шляхом {CREDENTIALS_FILE}"
        _sync_logger.warning("download_photo: %s", msg)
        return None, msg
    try:
        creds = Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        try:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        except TypeError:
            request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        data = buf.read()
        if not data:
            return None, "Drive API: порожня відповідь"
        return data, None
    except HttpError as e:
        status = getattr(e.resp, "status", None)
        _sync_logger.warning(
            "Drive API: не вдалося завантажити file_id=%s (HTTP %s). "
            "Надайте service account з credentials.json доступ до файлу/папки в Google Drive.",
            file_id,
            status,
        )
        if status == 404:
            return None, "Drive API 404: файл не знайдено або немає доступу (поділіться з service account)"
        if status == 403:
            return None, "Drive API 403: заборонено — додайте service account з credentials.json як читача файлу"
        return None, f"Drive API: помилка HTTP {status}"
    except Exception as e:
        _sync_logger.warning("Drive API: помилка file_id=%s: %s", file_id, e)
        return None, f"Drive API: {e!s}"


def _content_from_bytes(data: bytes) -> tuple[ContentFile | None, str | None]:
    if _bytes_look_like_image(data):
        return ContentFile(data), None
    if not _response_looks_like_html(data) and len(data) > 200:
        return ContentFile(data), None
    if _response_looks_like_html(data):
        return None, "HTML-сторінка замість файлу"
    return None, "дані не схожі на зображення"


def _download_photo_via_http(file_id: str) -> tuple[ContentFile | None, str | None]:
    """
    Резерв після Drive API. Великі файли в Google часто віддають HTML + cookie download_warning;
    без повторного запиту з confirm — бінарник не отримати.
    """
    session = requests.Session()
    base = "https://drive.google.com/uc"
    params = {"export": "download", "id": file_id}
    try:
        r = session.get(base, params=params, timeout=120)
        if r.status_code != 200:
            return None, f"uc export: HTTP {r.status_code}"

        cf, err = _content_from_bytes(r.content)
        if cf is not None:
            return cf, None

        if not _response_looks_like_html(r.content):
            return None, err or "невідомий формат від uc export"

        confirm = None
        for cookie in session.cookies:
            if cookie.name.startswith("download_warning"):
                confirm = cookie.value
                break
        if confirm is None:
            m = re.search(r"confirm=([0-9A-Za-z_-]+)", r.text[:200000])
            if m:
                confirm = m.group(1)
        if confirm:
            r2 = session.get(
                base,
                params={"export": "download", "id": file_id, "confirm": confirm},
                timeout=120,
            )
            if r2.status_code == 200:
                cf2, err2 = _content_from_bytes(r2.content)
                if cf2 is not None:
                    return cf2, None
                if err2:
                    _sync_logger.debug("uc confirm retry: %s file_id=%s", err2, file_id)

        r3 = session.get(
            "https://docs.google.com/uc",
            params={"export": "download", "id": file_id},
            timeout=120,
        )
        if r3.status_code == 200:
            cf3, _ = _content_from_bytes(r3.content)
            if cf3 is not None:
                return cf3, None
            for cookie in session.cookies:
                if cookie.name.startswith("download_warning"):
                    r4 = session.get(
                        "https://docs.google.com/uc",
                        params={
                            "export": "download",
                            "id": file_id,
                            "confirm": cookie.value,
                        },
                        timeout=120,
                    )
                    if r4.status_code == 200:
                        cf4, _ = _content_from_bytes(r4.content)
                        if cf4 is not None:
                            return cf4, None
                    break

        return None, (
            "Google uc export: замість зображення HTML (немає доступу до файлу в Drive для service account "
            "або потрібне підтвердження завантаження для великого файлу)"
        )
    except Exception as e:
        _sync_logger.warning("uc export exception file_id=%s: %s", file_id, e)
        return None, f"uc export: {e!s}"


def _download_photo_direct_http(url: str) -> tuple[ContentFile | None, str | None]:
    """Пряме посилання на файл (не Google Drive file id): CDN, Imgur, тощо."""
    try:
        r = requests.get(
            url,
            timeout=120,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GiveMeCatalogSync/1.0)"},
        )
        if r.status_code != 200:
            return None, f"пряме посилання: HTTP {r.status_code}"
        data = r.content
        if len(data) > 25 * 1024 * 1024:
            return None, "файл занадто великий (>25 МБ)"
        cf, err = _content_from_bytes(data)
        if cf is not None:
            return cf, None
        return None, err or "пряме посилання: не зображення"
    except Exception as e:
        _sync_logger.warning("direct photo HTTP failed url=%s: %s", url[:220], e)
        return None, f"пряме посилання: {e!s}"


def download_photo(link) -> tuple[ContentFile | None, str | None]:
    """
    Спочатку Google Drive API (file id), інакше uc?export=download з confirm;
    прямі https на зображення (не drive.google.com) — окремий GET.
    Повертає (файл, None) або (None, короткий текст причини для логів/Telegram).
    """
    try:
        s = (link or "").strip()
        if not s:
            return None, "порожнє посилання"
        file_id = _drive_file_id(s)
        if file_id:
            data, api_err = _download_photo_via_drive_api(file_id)
            if data:
                cf, conv_err = _content_from_bytes(data)
                if cf is not None:
                    return cf, None
                _sync_logger.debug(
                    "download_photo: Drive API не JPEG/PNG, пробуємо HTTP file_id=%s (%s)",
                    file_id,
                    conv_err,
                )

            cf_http, http_err = _download_photo_via_http(file_id)
            if cf_http is not None:
                return cf_http, None
            parts = [x for x in (api_err, http_err) if x]
            return None, " / ".join(parts) if parts else "не вдалось завантажити з Drive"

        low = s.lower()
        if low.startswith(("http://", "https://")) and "drive.google.com" not in low:
            return _download_photo_direct_http(s)
        if "drive.google.com" in low and not file_id:
            return None, "посилання на Drive, але не вдалось витягти file id з тексту комірки"
        return None, "не знайдено file id і це не пряме https-посилання на файл"
    except Exception as e:
        _sync_logger.exception("download_photo failed link=%s: %s", link, e)
        return None, f"виняток: {e!s}"


def get_google_sheet_data(spreadsheet_id, range_name):
    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)

    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get("values", [])

    return values
