/**
 * Фільтри розмірів у каталозі: пресети за назвою каталогу (як у Django / імпорті),
 * плюс підмішування реальних розмірів з завантажених товарів (пагінація, нові артикули).
 * Раніше використовувались жорстко прошиті id каталогів — у продакшені вони не збігалися з БД.
 */

export type SizeOption = { label: string; value: string };

export const sizesOptions = {
    numeric: [
        { label: "28", value: "28" },
        { label: "29", value: "29" },
        { label: "30", value: "30" },
        { label: "31", value: "31" },
        { label: "32", value: "32" },
        { label: "33", value: "33" },
        { label: "34", value: "34" },
        { label: "35", value: "35" },
        { label: "36", value: "36" },
        { label: "38", value: "38" },
        { label: "39", value: "39" },
        { label: "40", value: "40" },
        { label: "41", value: "41" },
        { label: "42", value: "42" },
        { label: "43", value: "43" },
        { label: "44", value: "44" },
        { label: "45", value: "45" },
        { label: "46", value: "46" },
    ],
    shoe: [
        { label: "38", value: "38" },
        { label: "39", value: "39" },
        { label: "40", value: "40" },
        { label: "41", value: "41" },
        { label: "42", value: "42" },
        { label: "43", value: "43" },
        { label: "44", value: "44" },
        { label: "45", value: "45" },
        { label: "46", value: "46" },
        { label: "47", value: "47" },
    ],
    letter: [
        { label: "S", value: "S" },
        { label: "M", value: "M" },
        { label: "L", value: "L" },
        { label: "XL", value: "XL" },
        { label: "2XL", value: "2XL" },
        { label: "3XL", value: "3XL" },
        { label: "4XL", value: "4XL" },
        { label: "5XL", value: "5XL" },
        { label: "6XL", value: "6XL" },
        { label: "7XL", value: "7XL" },
    ],
} as const;

/** Назви каталогів з server/shop/catalog_sheet_sources.py (поле Catalog.title). */
const SHOE_CATALOG_TITLES = new Set([
    "Взуття весна /осінь",
    "Взуття зима",
    "Взуття літо",
]);

const NUMERIC_CATALOG_TITLES = new Set([
    "Джинси",
    "Штани",
    "Шорти джинсові",
    "Шорти текстильні",
]);

const LETTER_CATALOG_TITLES = new Set([
    "Кофти",
    "Костюми весна /осінь",
    "Костюми зима",
    "Костюми літо",
    "Куртки",
    "Жилетки",
    "Спортивні штани",
    "Футболки",
    "Поло",
    "Сорочки",
    "Труси",
    "Шорти плавальні",
]);

function normTitle(t: string): string {
    return t.replace(/\s+/g, " ").trim();
}

/** Пресет списку розмірів за назвою каталогу; null — лише динамічні розміри з товарів. */
export function getPresetSizeOptionsForCatalogTitle(title: string | undefined): SizeOption[] | null {
    if (!title) return null;
    const t = normTitle(title);
    if (SHOE_CATALOG_TITLES.has(t)) return [...sizesOptions.shoe];
    if (NUMERIC_CATALOG_TITLES.has(t)) return [...sizesOptions.numeric];
    if (LETTER_CATALOG_TITLES.has(t)) return [...sizesOptions.letter];
    return null;
}

const LETTER_ORDER = ["XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL", "7XL", "8XL"];

function sortSizeLabels(labels: string[]): string[] {
    const rank = (raw: string): { kind: "letter"; i: number } | { kind: "num"; n: number } | { kind: "str"; s: string } => {
        const s = raw.trim();
        const u = s.toUpperCase().replace(/\s+/g, "");
        const li = LETTER_ORDER.findIndex((x) => x.toUpperCase() === u);
        if (li >= 0) return { kind: "letter", i: li };
        const n = parseFloat(s.replace(",", "."));
        if (!Number.isNaN(n) && /^[\d.,]+$/.test(s.trim())) return { kind: "num", n };
        return { kind: "str", s: s.toLowerCase() };
    };
    const kindOrder = { num: 0, letter: 1, str: 2 };
    return [...labels].sort((a, b) => {
        const ra = rank(a);
        const rb = rank(b);
        if (ra.kind !== rb.kind) return kindOrder[ra.kind] - kindOrder[rb.kind];
        if (ra.kind === "num" && rb.kind === "num") return ra.n - rb.n;
        if (ra.kind === "letter" && rb.kind === "letter") return ra.i - rb.i;
        if (ra.kind === "str" && rb.kind === "str") return ra.s.localeCompare(rb.s, "uk");
        return 0;
    });
}

/** Унікальні активні розміри з масиву товарів (після завантаження сторінок). */
export function sizeOptionsFromProducts(
    products: Array<{ product_properties?: Array<{ title?: string | null }> }>,
): SizeOption[] {
    const seen = new Set<string>();
    const raw: string[] = [];
    for (const p of products || []) {
        for (const prop of p.product_properties || []) {
            const t = prop.title?.trim();
            if (!t) continue;
            const key = t.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            raw.push(t);
        }
    }
    return sortSizeLabels(raw).map((v) => ({ label: v, value: v }));
}

/** Опції для селекта: пресет + унікальні розміри з даних (щоб не губити нестандартні значення з таблиці). */
export function getCatalogSizeFilterOptions(
    catalogTitle: string | undefined,
    products: Array<{ product_properties?: Array<{ title?: string | null }> }>,
): SizeOption[] {
    const preset = getPresetSizeOptionsForCatalogTitle(catalogTitle);
    const fromProducts = sizeOptionsFromProducts(products);
    if (!preset?.length) return fromProducts;

    const byNorm = new Map<string, string>();
    for (const o of preset) {
        byNorm.set(o.value.trim().toLowerCase(), o.value);
    }
    for (const o of fromProducts) {
        const k = o.value.trim().toLowerCase();
        if (!byNorm.has(k)) byNorm.set(k, o.value);
    }
    return sortSizeLabels(Array.from(byNorm.values())).map((v) => ({ label: v, value: v }));
}

/** Порівняння розміру у фільтрі з полем варіанта (різні пробіли / регістр для L/xl). */
export function propertyTitleMatchesSize(propertyTitle: string | undefined, selectedSize: string): boolean {
    if (!propertyTitle || !selectedSize) return false;
    const a = propertyTitle.trim();
    const b = selectedSize.trim();
    if (a === b) return true;
    const na = parseFloat(a.replace(",", "."));
    const nb = parseFloat(b.replace(",", "."));
    if (!Number.isNaN(na) && !Number.isNaN(nb) && na === nb) return true;
    return a.toUpperCase() === b.toUpperCase();
}
