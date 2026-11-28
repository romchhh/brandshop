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
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.functions import Lower, Trim
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
    notify_sync_fatal_error,
    notify_sync_started,
    send_catalog_sync_message,
    send_sync_finish_message,
)

_SERVER_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE") or str(_SERVER_ROOT / "credentials.json")
_sync_logger = logging.getLogger(__name__)


class _SyncLogBridge:
    """Під час run_product_sync дублює повідомлення в log() (Celery / manage.py), не лише в django.logging."""

    fn: Callable[[str], None] | None = None


def _sync_emit(msg: str) -> None:
    """Завжди WARNING у логері (видно за замовчуванням) + той самий текст у log(...) імпорту."""
    _sync_logger.warning(msg)
    fn = _SyncLogBridge.fn
    if callable(fn):
        try:
            fn(msg)
        except Exception:
            pass


def _sync_log_line(msg: str) -> None:
    """Помилки/етапи завантаження фото: WARNING у логер + у stdout (log) лише під час синхронізації."""
    _sync_logger.warning(msg)
    if _sync_import_active and callable(_SyncLogBridge.fn):
        try:
            _SyncLogBridge.fn(msg)
        except Exception:
            pass


# Типовий id файлу в Google Drive (лише символи, без слешів — якщо вставили id у комірку без URL)
_BARE_DRIVE_FILE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{27,100}$")

# Під час run_product_sync — лічильники для Telegram по поточному блоці каталогу
_sync_import_active = False
_sync_block: dict = {}


def _sync_import_set_active(value: bool) -> None:
    global _sync_import_active
    _sync_import_active = value


def _catalog_sync_tg_verbose() -> bool:
    return bool(getattr(settings, "CATALOG_SYNC_TG_VERBOSE", False))


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
        "photo_unrecognized_samples": [],
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


def sync_block_photo_cell_unrecognized(detail: str = "") -> None:
    """У колонці фото щось є, але це не схоже на http(s) / Drive — імпорт фото пропущено."""
    if not _sync_import_active:
        return
    _sync_block["photo_cell_unrecognized"] = int(_sync_block.get("photo_cell_unrecognized", 0)) + 1
    if detail:
        samples: list = _sync_block.setdefault("photo_unrecognized_samples", [])
        if len(samples) < 6:
            samples.append(detail[:450])


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


def _photo_import_source_label(cell) -> str:
    """Стабільний відбиток посилання (≤64). Якщо не змінилось — фото не качаємо знову."""
    import hashlib

    raw = "" if cell is None else str(cell).strip()
    if not raw:
        return ""
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:40]


def _photo_unchanged(product, cell) -> bool:
    """True — файл уже є і посилання в таблиці те саме."""
    label = _photo_import_source_label(cell)
    if not label:
        return False
    current = (getattr(product, "photo_import_source", "") or "").strip()
    name = ""
    try:
        name = (product.photo.name or "").strip() if product.photo else ""
    except Exception:
        name = ""
    if not name:
        return False
    if current == label:
        return True
    # Старі мітки drive/url без хеша: один раз фіксуємо відбиток, без повторного завантаження.
    if current in {"drive", "url"}:
        product.photo_import_source = label
        product.save(update_fields=["photo_import_source"])
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
    if _looks_like_bare_drive_file_id(s):
        return True
    return False


def _photo_cell_preview_for_log(cell, max_len: int = 220) -> str:
    """Що саме прийшло з Google Sheets у колонці фото — для логів і Telegram (один рядок, обрізано)."""
    if cell is None:
        return "(порожньо)"
    s = str(cell).replace("\n", " ").replace("\r", " ").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _photo_fail_detail(article: str, cell, ph_err: str | None) -> str:
    prev = _photo_cell_preview_for_log(cell, max_len=200)
    return f"арт.{article}: з таблиці «{prev}» → {ph_err or 'невідома причина'}"


def _verify_product_photo_saved(product: Product, article_label: str) -> None:
    """Після product.photo.save — перевірка в БД (refresh) і за можливості наявності файлу в storage."""
    product.refresh_from_db(fields=["photo"])
    name = (product.photo.name or "").strip()
    if not name:
        msg = (
            f"🔴 sync photo DB: article={article_label} — поле photo в БД порожнє після збереження "
            f"(перевір MEDIA_ROOT і права запису)"
        )
        _sync_logger.error(msg)
        _sync_emit(msg)
        return
    exists: bool | None = None
    try:
        exists = product.photo.storage.exists(name)
    except Exception as exc:
        _sync_logger.warning("sync photo DB: storage.exists(%s): %s", name, exc)
    if exists is False:
        msg = (
            f"🔴 sync photo DB: article={article_label} — у БД шлях «{name}», "
            f"але файл не знайдено в storage (клієнт може не отримати фото)"
        )
        _sync_logger.error(msg)
        _sync_emit(msg)
        return
    disk = "так" if exists is True else "не перевірено"
    _sync_emit(
        f"sync photo ok: article={article_label} — БД: «{name}»; файл у storage: {disk}"
    )


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
    prefetched = getattr(product, "_prefetched_objects_cache", None)
    if prefetched is not None and "product_properties" in prefetched:
        matches = [p for p in product.product_properties.all() if p.title == title]
        if matches:
            prop = min(matches, key=lambda p: p.pk)
            dup_pks = [p.pk for p in matches if p.pk != prop.pk]
            if dup_pks:
                ProductProperty.objects.filter(pk__in=dup_pks).delete()
            return prop

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


_catalog_cache: dict[str, Catalog] = {}
_article_cache: dict[str, Product] = {}
_sheet_titles_cache: dict[str, list[str]] = {}
_drive_service = None
_sheets_service = None

# Мережеві обриви Google API (довгий імпорт на 1GB VPS / idle keep-alive)
_GOOGLE_TRANSIENT = (
    BrokenPipeError,
    ConnectionError,
    ConnectionResetError,
    TimeoutError,
    OSError,
)


def _is_transient_google_error(exc: BaseException) -> bool:
    if isinstance(exc, HttpError):
        status = getattr(getattr(exc, "resp", None), "status", None)
        return status in (408, 429, 500, 502, 503, 504)
    if isinstance(exc, _GOOGLE_TRANSIENT):
        # Errno 32 Broken pipe, 104 Connection reset, 110 timed out
        errno = getattr(exc, "errno", None)
        if errno is not None and errno not in (32, 104, 110, 11, None):
            # Інші OSError (напр. «file not found») не ретраїмо
            if type(exc) is OSError and errno not in (32, 104, 110):
                return False
        return True
    name = type(exc).__name__
    msg = str(exc).lower()
    if "broken pipe" in msg or "connection reset" in msg or "timed out" in msg:
        return True
    if name in ("SSLEOFError", "SSLError", "IncompleteRead"):
        return True
    return False


def _reset_google_clients() -> None:
    """Скидає keep-alive клієнти після Broken pipe / reset."""
    global _sheets_service, _drive_service
    _sheets_service = None
    _drive_service = None


def _google_execute(request_factory, *, attempts: int = 6, label: str = "google-api"):
    """
    Виконує googleapiclient request з ретраями.
    request_factory: () -> HttpRequest — викликається щоразу (новий request після rebuild клієнта).
    """
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = request_factory()
            return req.execute(num_retries=2)
        except Exception as exc:
            last_exc = exc
            if not _is_transient_google_error(exc) or attempt >= attempts:
                raise
            _reset_google_clients()
            delay = min(2 ** (attempt - 1), 30)
            _sync_logger.warning(
                "%s: тимчасова помилка (%s), спроба %s/%s через %ss",
                label,
                exc,
                attempt,
                attempts,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _clear_sync_runtime_caches() -> None:
    global _catalog_cache, _article_cache, _sheet_titles_cache
    _catalog_cache = {}
    _article_cache = {}
    _sheet_titles_cache = {}
    _reset_google_clients()


def _warm_sync_runtime_caches() -> None:
    """Один прохід по БД замість SELECT на кожен рядок таблиці."""
    global _catalog_cache, _article_cache
    _catalog_cache = {c.title: c for c in Catalog.objects.all()}
    _article_cache = {}
    dup_pks: list[int] = []
    products = (
        Product.objects.select_related("catalog")
        .prefetch_related("product_properties")
        .order_by("pk")
    )
    for product in products:
        key = _normalize_article(product.article).lower()
        if not key:
            continue
        prev = _article_cache.get(key)
        if prev is None:
            _article_cache[key] = product
        elif product.pk < prev.pk:
            dup_pks.append(prev.pk)
            _article_cache[key] = product
        else:
            dup_pks.append(product.pk)
    if dup_pks:
        Product.objects.filter(pk__in=dup_pks).update(active=False)


def _cache_product(product: Product) -> None:
    key = _normalize_article(product.article).lower()
    if key:
        _article_cache[key] = product


def _get_or_create_catalog(catalog_title: str) -> Catalog:
    cached = _catalog_cache.get(catalog_title)
    if cached is not None:
        return cached
    catalog = Catalog.objects.filter(title=catalog_title).first()
    if catalog is None:
        catalog = Catalog.objects.create(title=catalog_title)
    _catalog_cache[catalog_title] = catalog
    return catalog


def _normalize_article(raw) -> str:
    """Єдиний формат артикула для синку (trim + collapse whitespace)."""
    s = str(raw).replace("\xa0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _pick_product_for_article(article: str) -> Product | None:
    """
    Повертає "основний" товар для артикула.
    Якщо дублі вже є — лишаємо найменший pk активним, решту деактивуємо,
    щоб каталог не показував 5-10 однакових карток.
    """
    if not article:
        return None
    key = article.lower()
    if key in _article_cache:
        return _article_cache[key]
    qs = (
        Product.objects.annotate(article_norm=Lower(Trim("article")))
        .filter(article_norm=key)
        .order_by("pk")
    )
    keep = qs.first()
    if keep is None:
        return None
    dup_ids = list(qs.exclude(pk=keep.pk).values_list("pk", flat=True))
    if dup_ids:
        Product.objects.filter(pk__in=dup_ids).update(active=False)
        _sync_emit(
            f"sync dedupe: article={article} — деактивовано дублікатів: {len(dup_ids)} (залишено id={keep.pk})"
        )
    _article_cache[key] = keep
    return keep


def _unlink_media_name(name: str) -> bool:
    """Видаляє файл у MEDIA_ROOT. Повертає True, якщо файл був і його прибрано."""
    rel = (name or "").strip().lstrip("/")
    if not rel or ".." in Path(rel).parts:
        return False
    path = Path(settings.MEDIA_ROOT) / rel
    try:
        if path.is_file():
            path.unlink()
            return True
    except OSError:
        _sync_logger.warning("Не вдалося видалити медіа %s", path, exc_info=True)
    return False


def _retire_product(product: Product) -> str:
    """
    Товар зник із таблиць.
    Якщо він є в замовленнях — ховаємо з каталогу і стираємо фото, рядок лишаємо для історії.
    Інакше видаляємо разом із розмірами, переглядами і кошиком.
    """
    from shop.models import BasketItem, OrderItem, ProductView

    names = []
    if product.photo and product.photo.name:
        names.append(product.photo.name)
    for prop in product.product_properties.all().only("id", "photo"):
        if prop.photo and prop.photo.name:
            names.append(prop.photo.name)
    for name in names:
        _unlink_media_name(name)

    has_orders = OrderItem.objects.filter(product_id=product.pk).exists()
    if has_orders:
        product.photo = None
        product.active = False
        product.save(update_fields=["photo", "active"])
        product.product_properties.update(photo="", active=False)
        BasketItem.objects.filter(product_id=product.pk).delete()
        return "hidden"
    BasketItem.objects.filter(product_id=product.pk).delete()
    ProductView.objects.filter(product_id=product.pk).delete()
    product.product_properties.all().delete()
    product.photo = None
    product.delete()
    return "deleted"


def _delete_orphan_product_media() -> int:
    """Файли в product_photos / product_property_photos, на які вже ніхто не посилається."""
    referenced: set[str] = set()
    for name in Product.objects.exclude(photo__isnull=True).exclude(photo="").values_list("photo", flat=True):
        if name:
            referenced.add(str(name))
    for name in ProductProperty.objects.exclude(photo__isnull=True).exclude(photo="").values_list("photo", flat=True):
        if name:
            referenced.add(str(name))

    removed = 0
    root = Path(settings.MEDIA_ROOT)
    for folder in ("product_photos", "product_property_photos"):
        base = root / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel in referenced:
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                _sync_logger.warning("Не вдалося видалити осиротіле медіа %s", path, exc_info=True)
    return removed


def _prune_products_missing_from_sheets(
    seen_by_catalog: dict[str, set[str]],
    loaded_catalogs: set[str],
    unsafe_catalogs: set[str],
    log,
) -> tuple[int, int, int]:
    """
    Прибирає товари каталогів, які цього разу успішно прочитані з таблиці,
    але їхнього артикула в рядках уже немає.
    Порожня відповідь таблиці або помилка читання каталог не чіпає.
    """
    deleted = 0
    hidden = 0
    for title in loaded_catalogs:
        if title in unsafe_catalogs:
            log(f"Каталог «{title}» не чистимо: таблицю не вдалося прочитати повністю.")
            continue
        articles = seen_by_catalog.get(title, set())
        ids = list(
            Product.objects.filter(catalog__title=title)
            .exclude(article="")
            .values_list("pk", flat=True)
        )
        for pk in ids:
            product = Product.objects.filter(pk=pk).first()
            if product is None:
                continue
            key = _normalize_article(product.article).lower()
            if key in articles:
                continue
            outcome = _retire_product(product)
            if outcome == "deleted":
                deleted += 1
            else:
                hidden += 1
    orphans = _delete_orphan_product_media()
    log(
        f"Прибирання після імпорту: видалено товарів {deleted}, "
        f"сховано (є в замовленнях) {hidden}, зайвих файлів фото {orphans}."
    )
    return deleted, hidden, orphans


def run_product_sync(log=print, *, trigger: str = "schedule"):
    """
    Імпорт/оновлення товарів з Google Таблиць (логіка спільна з manage.py update_products).
    log: callable(str) — для виводу прогресу (наприклад self.stdout.write у команді).
    """
    from shop.sync_schedule import mark_sync_finished, mark_sync_started, update_sync_progress

    if not mark_sync_started(trigger):
        log("Синхронізація вже виконується — повторний запуск пропущено.")
        return
    t0 = time.monotonic()
    row_errors: list[str] = []
    sheet_errors: list[str] = []
    catalogs_completed = 0
    rows_processed = 0
    total_photo_fail = 0
    total_photo_unrecognized = 0
    seen_by_catalog: dict[str, set[str]] = {}
    loaded_catalogs: set[str] = set()
    unsafe_catalogs: set[str] = set()

    notify_sync_started(source="Імпорт")
    _clear_sync_runtime_caches()
    try:
        _warm_sync_runtime_caches()
        log(f"Кеш артикулів: {len(_article_cache)}, каталогів: {len(_catalog_cache)}")
    except Exception as exc:
        _sync_logger.warning("warm sync cache failed", exc_info=True)
        row_errors.append(f"Прогрів кешу · {exc!s}")

    if _catalog_sync_tg_verbose():
        send_catalog_sync_message("🔄 (детальний режим) проміжні повідомлення по блоках увімкнено…")
    _sync_import_set_active(True)
    _SyncLogBridge.fn = log
    jobs = list(iter_catalog_import_jobs())
    job_count = max(len(jobs), 1)
    last_progress_at = 0.0

    def report(fraction: float, label: str, *, force: bool = False) -> None:
        nonlocal last_progress_at
        now = time.monotonic()
        if not force and now - last_progress_at < 1.2:
            return
        last_progress_at = now
        try:
            update_sync_progress(fraction, label)
        except Exception:
            _sync_logger.warning("sync progress update failed", exc_info=True)

    try:
        report(0.01, "Читаю таблиці…", force=True)
        for job_index, (catalog_title, spreadsheet_id, fields) in enumerate(jobs):
            range_name = fields["sheet"]
            if not isinstance(range_name, list):
                range_name = [range_name]

            job_base = job_index / job_count
            job_span = 1 / job_count
            log(
                f"--- Каталог «{catalog_title}» · spreadsheet={spreadsheet_id} · sheet index(es)={range_name} ---"
            )
            report(
                job_base,
                f"«{catalog_title}» · таблиця {job_index + 1} з {len(jobs)}",
                force=True,
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
                unsafe_catalogs.add(catalog_title)
                continue

            if len(rows) == 0:
                log("Таблиця порожня або діапазон не знайдено — каталог не чистимо.")
                unsafe_catalogs.add(catalog_title)
                if _catalog_sync_tg_verbose():
                    send_catalog_sync_message(format_block_empty(catalog_title, spreadsheet_id))
                catalogs_completed += 1
                continue

            loaded_catalogs.add(catalog_title)
            _sync_block_reset(catalog_title, spreadsheet_id, range_name, len(rows))
            if _catalog_sync_tg_verbose():
                send_catalog_sync_message(
                    format_block_start(catalog_title, spreadsheet_id, range_name, len(rows))
                )

            ind = 1
            row_total = max(len(rows), 1)
            for row in rows:
                if ind == 1 or ind % 200 == 0:
                    log(f"{catalog_title}: {ind} / {len(rows)}")
                if ind == 1 or ind % 100 == 0 or ind == len(rows):
                    report(
                        job_base + job_span * (min(ind, row_total) / row_total),
                        f"«{catalog_title}» · {min(ind, len(rows))} / {len(rows)} · таблиця {job_index + 1} з {len(jobs)}",
                    )
                ind += 1
                if fields["article"] >= len(row):
                    continue
                if _is_likely_header_row(row, fields):
                    continue

                art = _normalize_article(row[fields["article"]]) if fields["article"] < len(row) else ""
                if not art:
                    continue
                seen_by_catalog.setdefault(catalog_title, set()).add(art.lower())
                try:
                    existing = _pick_product_for_article(art)
                    if existing is None:
                        create_product(row, fields, catalog_title, art)
                    else:
                        update_product(existing, row, fields, catalog_title)
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
            report(
                (job_index + 1) / job_count,
                f"Готово «{catalog_title}» · {job_index + 1} з {len(jobs)}",
                force=True,
            )
            log(f"--- Завершено блок: «{catalog_title}» / {spreadsheet_id} ---")
            pf = int(_sync_block.get("photo_fail", 0))
            pu = int(_sync_block.get("photo_cell_unrecognized", 0))
            total_photo_fail += pf
            total_photo_unrecognized += pu
            if pf > 0 or pu > 0:
                msg = (
                    f"🔴 КРИТИЧНО (фото): блок «{catalog_title}» — не завантажено: {pf}, "
                    f"комірка не URL: {pu}"
                )
                _sync_logger.error(msg)
                log(msg)
            if _catalog_sync_tg_verbose():
                send_catalog_sync_message(
                    format_block_done(
                        catalog_title,
                        spreadsheet_id,
                        _sync_block.get("rows_ok", 0),
                        _sync_block.get("rows_err", 0),
                        pf,
                        list(_sync_block.get("err_samples") or []),
                        photo_cell_unrecognized=pu,
                        photo_fail_samples=list(_sync_block.get("photo_fail_samples") or []),
                        photo_unrecognized_samples=list(_sync_block.get("photo_unrecognized_samples") or []),
                    )
                )
    except Exception as exc:
        duration = time.monotonic() - t0
        _sync_logger.exception("run_product_sync failed")
        notify_sync_fatal_error(exc, duration_sec=duration)
        mark_sync_finished(ok=False, rows_ok=rows_processed, message=str(exc)[:1500])
        _clear_sync_runtime_caches()
        raise
    finally:
        _SyncLogBridge.fn = None
        _sync_import_set_active(False)

    removed = hidden = orphans = 0
    report(0.97, "Прибираю товари і фото, яких уже немає", force=True)
    try:
        removed, hidden, orphans = _prune_products_missing_from_sheets(
            seen_by_catalog, loaded_catalogs, unsafe_catalogs, log
        )
    except Exception as exc:
        _sync_logger.exception("prune missing products failed")
        row_errors.append(f"Прибирання товарів · {exc!s}")

    try:
        from shop.promotional_rules import apply_last_active_variant_promotional_prices

        n_promo = apply_last_active_variant_promotional_prices()
        if n_promo:
            log(f"Акційні ціни (останній активний розмір): оновлено товарів — {n_promo}")
    except Exception as exc:
        _sync_logger.exception("apply_last_active_variant_promotional_prices failed")
        row_errors.append(f"Акційні ціни · {exc!s}")

    try:
        from django.core.cache import cache as _api_cache

        _api_cache.clear()
        log("Кеш API (Django) очищено після імпорту каталогу.")
    except Exception as exc:
        _sync_logger.warning("Не вдалося скинути Django cache після імпорту", exc_info=True)
        row_errors.append(f"Скидання кешу API · {exc!s}")

    duration = time.monotonic() - t0
    summary = format_sync_summary(
        duration_sec=duration,
        catalogs_completed=catalogs_completed,
        total_rows_iterated=rows_processed,
        row_errors=row_errors,
        sheet_errors=sheet_errors,
        total_photo_fail=total_photo_fail,
        total_photo_unrecognized=total_photo_unrecognized,
    )
    _sync_logger.info("Імпорт каталогу (повний підсумок у лог):\n%s", summary)
    send_sync_finish_message(
        duration_sec=duration,
        catalogs_completed=catalogs_completed,
        total_rows_iterated=rows_processed,
        row_errors=row_errors,
        sheet_errors=sheet_errors,
        total_photo_fail=total_photo_fail,
        total_photo_unrecognized=total_photo_unrecognized,
    )
    ok = not sheet_errors and not row_errors
    brief = (
        f"Рядків: {rows_processed}. Блоків: {catalogs_completed}. "
        f"Прибрано товарів: {removed}, сховано через замовлення: {hidden}, "
        f"зайвих фото: {orphans}. "
        f"Помилки таблиць: {len(sheet_errors)}, рядків: {len(row_errors)}."
    )
    mark_sync_finished(ok=ok, rows_ok=rows_processed, message=brief)
    if total_photo_fail > 0 or total_photo_unrecognized > 0:
        msg = (
            f"🔴 КРИТИЧНО — підсумок фото за весь імпорт: не завантажено файл: {total_photo_fail}, "
            f"комірка не URL: {total_photo_unrecognized}"
        )
        _sync_logger.error(msg)
        log(msg)
    _clear_sync_runtime_caches()


def get_catalog_data(SPREADSHEET_ID, RANGE_NAME):
    if not isinstance(RANGE_NAME, list):
        RANGE_NAME = [RANGE_NAME]
    titles = _spreadsheet_sheet_titles(SPREADSHEET_ID)
    for i in RANGE_NAME:
        if i < 0 or i >= len(titles):
            raise ValueError(f"Індекс аркуша {i} поза межами (0 - {len(titles) - 1}).")
    if len(RANGE_NAME) == 1:
        sheet_title = titles[RANGE_NAME[0]]

        def _one():
            return (
                _sheets_api()
                .spreadsheets()
                .values()
                .get(spreadsheetId=SPREADSHEET_ID, range=sheet_title)
            )

        result = _google_execute(_one, label=f"sheets.get:{SPREADSHEET_ID[:8]}")
        return result.get("values", [])
    ranges = [titles[i] for i in RANGE_NAME]

    def _batch():
        return (
            _sheets_api()
            .spreadsheets()
            .values()
            .batchGet(spreadsheetId=SPREADSHEET_ID, ranges=ranges)
        )

    result = _google_execute(_batch, label=f"sheets.batchGet:{SPREADSHEET_ID[:8]}")
    data: list = []
    for block in result.get("valueRanges", []):
        data.extend(block.get("values", []))
    return data


def _spreadsheet_sheet_titles(spreadsheet_id: str) -> list[str]:
    """Назви вкладок таблиці — один spreadsheets.get на файл за синхронізацію."""
    if spreadsheet_id not in _sheet_titles_cache:

        def _meta():
            return _sheets_api().spreadsheets().get(spreadsheetId=spreadsheet_id)

        spreadsheet = _google_execute(_meta, label=f"sheets.meta:{spreadsheet_id[:8]}")
        _sheet_titles_cache[spreadsheet_id] = [
            s["properties"]["title"] for s in spreadsheet.get("sheets", [])
        ]
    return _sheet_titles_cache[spreadsheet_id]


def _sheets_api():
    """Один клієнт Sheets на процес — менше handshake і менше шансів упертись у квоту."""
    global _sheets_service
    if _sheets_service is None:
        creds = Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        _sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return _sheets_service


def get_sheet_id_by_index(spreadsheet_id, sheet_index):
    titles = _spreadsheet_sheet_titles(spreadsheet_id)
    if sheet_index < 0 or sheet_index >= len(titles):
        raise ValueError(f"Індекс аркуша {sheet_index} поза межами (0 - {len(titles) - 1}).")
    return titles[sheet_index]


def get_google_sheet_data_by_index(spreadsheet_id, sheet_index, range_name=None):
    sheet_title = get_sheet_id_by_index(spreadsheet_id, sheet_index)

    full_range = sheet_title if not range_name else f"{sheet_title}!{range_name}"

    def _vals():
        return (
            _sheets_api()
            .spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=full_range)
        )

    result = _google_execute(_vals, label=f"sheets.values:{spreadsheet_id[:8]}")
    return result.get("values", [])


def update_product(product: Product, row, fields, catalog_title):
    dirty: set[str] = set()

    def mark(field: str, value) -> None:
        if getattr(product, field) != value:
            setattr(product, field, value)
            dirty.add(field)

    def flush() -> None:
        if dirty:
            product.save(update_fields=sorted(dirty))
            dirty.clear()

    def deactivate_return() -> None:
        mark("active", False)
        flush()
        return

    target_catalog = _get_or_create_catalog(catalog_title)
    if product.catalog_id != target_catalog.id:
        next_priority = (
            Product.objects.filter(catalog=target_catalog)
            .exclude(pk=product.pk)
            .order_by("-priority")
            .values_list("priority", flat=True)
            .first()
        )
        mark("catalog", target_catalog)
        mark("priority", (next_priority + 1) if next_priority else 1)
        flush()
        _sync_emit(
            f"sync move: article={product.article} — категорія змінена на «{target_catalog.title}»"
        )

    if fields["title"] < len(row) and row[fields["title"]] != "":
        mark("active", True)
        mark("title", row[fields["title"]])
    else:
        mark("active", False)
        flush()
        return

    if fields["price"] < len(row):
        raw_p = row[fields["price"]]
        if str(raw_p).strip() != "":
            price_dec = _normalize_price(raw_p)
            if price_dec is not None:
                mark("active", True)
                mark("price", price_dec)
            else:
                return deactivate_return()
        else:
            return deactivate_return()
    else:
        return deactivate_return()

    if (fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] == "") or (
        fields.get("count") is not None and fields["count"] < len(row) and row[fields["count"]] == ""
    ):
        return deactivate_return()
    if fields.get("count") is not None and fields["count"] < len(row) and row[fields["count"]] != "":
        mark("active", True)
    elif fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] != "":
        mark("active", True)

    if fields.get("size") is not None and fields["size"] < len(row) and row[fields["size"]] != "":
        sizes = _sizes_from_row(row, fields)

        if len(sizes) == 0 or (fields["price"] < len(row) and _normalize_price(row[fields["price"]]) is None):
            return deactivate_return()

        if sizes:
            want = set(sizes)
            ProductProperty.objects.filter(product=product).exclude(title__in=want).update(active=False)
            for size in sizes:
                prop = _merge_product_property(product, size)
                if not prop.active:
                    prop.active = True
                    prop.save(update_fields=["active"])

    if fields.get("count") is not None and fields["count"] < len(row):
        cnt = str(row[fields["count"]]).strip()
        if cnt:
            prop = _merge_product_property(product, cnt)
            if not prop.active:
                prop.active = True
                prop.save(update_fields=["active"])

    if fields.get("description") is not None and fields["description"] < len(row):
        mark("description", str(row[fields["description"]]))

    flush()

    if fields["photo"] < len(row):
        cell = row[fields["photo"]]
        raw = str(cell).strip() if cell is not None else ""
        if not raw:
            _sync_logger.debug("sync photo skip empty cell: article=%s", product.article)
        elif raw and not _photo_cell_usable(cell):
            pv = _photo_cell_preview_for_log(cell)
            _sync_emit(
                f"sync photo: article={product.article} — комірка не схожа на URL, з таблиці: «{pv}»"
            )
            sync_block_photo_cell_unrecognized(
                f"арт.{product.article}: «{pv}» (потрібен https або посилання Google Drive / id файлу)"
            )
        elif _photo_unchanged(product, cell):
            pass
        elif _photo_cell_usable(cell):
            pv = _photo_cell_preview_for_log(cell)
            _sync_emit(f"sync photo try: article={product.article} — посилання з таблиці: «{pv}»")
            ph, ph_err = download_photo(cell)
            if ph is not None:
                # Видаляємо старий файл лише після успішного завантаження нового,
                # щоб не накопичувались дублікати з суфіксами (_DnryELM, _ah4e0tR…).
                # Django додає суфікс якщо файл вже існує — тому явно видаляємо і очищаємо поле.
                if product.photo and product.photo.name:
                    try:
                        product.photo.storage.delete(product.photo.name)
                    except Exception:
                        pass
                    product.photo = None
                    product.save(update_fields=["photo"])
                product.photo_import_source = _photo_import_source_label(cell)
                product.photo.save(f"{product.article}_main.jpg", ph, save=True)
                _verify_product_photo_saved(product, str(product.article))
            else:
                detail = _photo_fail_detail(str(product.article), cell, ph_err)
                _sync_emit(f"sync photo failed: {detail}")
                sync_block_photo_fail(detail)


def create_product(row, fields, catalog_title, article: str):
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

    catalog = _get_or_create_catalog(catalog_title)

    product = Product.objects.create(
        title=str(row[fields["title"]]).strip(),
        article=article,
        price=price_dec,
        catalog=catalog,
        description=desc,
    )

    if fields["photo"] < len(row):
        cell = row[fields["photo"]]
        raw = str(cell).strip() if cell is not None else ""
        art = article
        if not raw:
            _sync_logger.debug("sync photo skip empty cell: article=%s", art)
        elif raw and not _photo_cell_usable(cell):
            pv = _photo_cell_preview_for_log(cell)
            _sync_emit(
                f"sync photo: article={art} — комірка не схожа на URL, з таблиці: «{pv}»"
            )
            sync_block_photo_cell_unrecognized(
                f"арт.{art}: «{pv}» (потрібен https або посилання Google Drive / id файлу)"
            )
        elif _photo_cell_usable(cell):
            pv = _photo_cell_preview_for_log(cell)
            _sync_emit(f"sync photo try: article={art} — посилання з таблиці: «{pv}»")
            photo, ph_err = download_photo(cell)
            if photo is not None:
                if product.photo and product.photo.name:
                    try:
                        product.photo.storage.delete(product.photo.name)
                    except Exception:
                        pass
                    product.photo = None
                    product.save(update_fields=["photo"])
                product.photo_import_source = _photo_import_source_label(cell)
                product.photo.save(f"{article}_main.jpg", photo, save=True)
                _verify_product_photo_saved(product, art)
            else:
                detail = _photo_fail_detail(art, cell, ph_err)
                _sync_emit(f"sync photo failed: {detail}")
                sync_block_photo_fail(detail)

    for size in dict.fromkeys(sizes):
        _merge_product_property(product, size)

    if not sizes and fields.get("count") is not None and fields["count"] < len(row):
        cnt = str(row[fields["count"]]).strip()
        if cnt:
            _merge_product_property(product, cnt)

    _cache_product(product)


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
        _sync_log_line(f"[sync photo download] Drive API: {msg}")
        return None, msg
    last_err: str | None = None
    for attempt in range(1, 5):
        try:
            global _drive_service
            if _drive_service is None:
                creds = Credentials.from_service_account_file(
                    CREDENTIALS_FILE,
                    scopes=["https://www.googleapis.com/auth/drive.readonly"],
                )
                _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
            service = _drive_service
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
                _sync_log_line(
                    f"[sync photo download] Drive API: порожня відповідь для file_id={file_id}"
                )
                return None, "Drive API: порожня відповідь"
            return data, None
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            if status in (408, 429, 500, 502, 503, 504) and attempt < 4:
                _reset_google_clients()
                time.sleep(min(2 ** (attempt - 1), 16))
                continue
            _sync_log_line(
                f"[sync photo download] Drive API: file_id={file_id} HTTP {status} — "
                f"надайте service account з credentials.json доступ до файлу/папки в Google Drive."
            )
            if status == 404:
                return None, "Drive API 404: файл не знайдено або немає доступу (поділіться з service account)"
            if status == 403:
                return None, "Drive API 403: заборонено — додайте service account з credentials.json як читача файлу"
            return None, f"Drive API: помилка HTTP {status}"
        except Exception as e:
            last_err = f"Drive API: {e!s}"
            if _is_transient_google_error(e) and attempt < 4:
                _reset_google_clients()
                _sync_log_line(
                    f"[sync photo download] Drive API: file_id={file_id} тимчасово ({e!s}), "
                    f"спроба {attempt}/4"
                )
                time.sleep(min(2 ** (attempt - 1), 16))
                continue
            _sync_log_line(f"[sync photo download] Drive API: file_id={file_id} виняток: {e!s}")
            return None, last_err
    return None, last_err or "Drive API: не вдалося завантажити"


def _content_from_bytes(data: bytes) -> tuple[ContentFile | None, str | None]:
    from shop.image_optimize import content_file_from_image_bytes

    if _bytes_look_like_image(data):
        return content_file_from_image_bytes(data), None
    if not _response_looks_like_html(data) and len(data) > 200:
        # Схоже на бінарник без magic — все одно пробуємо стиснути через Pillow
        try:
            return content_file_from_image_bytes(data), None
        except Exception:
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
            msg = f"uc export: HTTP {r.status_code}"
            _sync_log_line(f"[sync photo download] file_id={file_id} {msg}")
            return None, msg

        cf, err = _content_from_bytes(r.content)
        if cf is not None:
            return cf, None

        if not _response_looks_like_html(r.content):
            msg = err or "невідомий формат від uc export"
            _sync_log_line(f"[sync photo download] file_id={file_id} uc export: {msg}")
            return None, msg

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

        msg = (
            "Google uc export: замість зображення HTML (немає доступу до файлу в Drive для service account "
            "або потрібне підтвердження завантаження для великого файлу)"
        )
        _sync_log_line(f"[sync photo download] file_id={file_id} {msg}")
        return None, msg
    except Exception as e:
        _sync_log_line(f"[sync photo download] file_id={file_id} uc export виняток: {e!s}")
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
            msg = f"пряме посилання: HTTP {r.status_code}"
            _sync_log_line(f"[sync photo download] {msg} url={url[:200]}")
            return None, msg
        data = r.content
        if len(data) > 25 * 1024 * 1024:
            msg = "файл занадто великий (>25 МБ)"
            _sync_log_line(f"[sync photo download] {msg} url={url[:200]}")
            return None, msg
        cf, err = _content_from_bytes(data)
        if cf is not None:
            return cf, None
        msg = err or "пряме посилання: не зображення"
        _sync_log_line(f"[sync photo download] {msg} url={url[:200]}")
        return None, msg
    except Exception as e:
        _sync_log_line(f"[sync photo download] пряме посилання виняток url={url[:200]}: {e!s}")
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
            _sync_log_line("[sync photo download] порожнє посилання в комірці фото")
            return None, "порожнє посилання"
        file_id = _drive_file_id(s)
        if file_id:
            data, api_err = _download_photo_via_drive_api(file_id)
            if data:
                cf, conv_err = _content_from_bytes(data)
                if cf is not None:
                    return cf, None
                _sync_log_line(
                    f"[sync photo download] Drive API: відповідь не схожа на зображення, file_id={file_id}, "
                    f"пробуємо HTTP fallback ({conv_err or 'невідомо'})"
                )

            cf_http, http_err = _download_photo_via_http(file_id)
            if cf_http is not None:
                return cf_http, None
            parts = [x for x in (api_err, http_err) if x]
            err = " / ".join(parts) if parts else "не вдалось завантажити з Drive"
            _sync_log_line(f"[sync photo download] file_id={file_id} після API+HTTP: {err}")
            return None, err

        low = s.lower()
        if low.startswith(("http://", "https://")) and "drive.google.com" not in low:
            return _download_photo_direct_http(s)
        if "drive.google.com" in low and not file_id:
            msg = "посилання на Drive, але не вдалось витягти file id з тексту комірки"
            _sync_log_line(f"[sync photo download] {msg} комірка={s[:180]}")
            return None, msg
        msg = "не знайдено file id і це не пряме https-посилання на файл"
        _sync_log_line(f"[sync photo download] {msg} комірка={s[:180]}")
        return None, msg
    except Exception as e:
        _sync_logger.exception("download_photo failed link=%s: %s", link, e)
        _sync_log_line(f"[sync photo download] виняток: {e!s} link={str(link)[:200]}")
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
