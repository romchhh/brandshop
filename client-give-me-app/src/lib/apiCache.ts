/**
 * Кеш GET-лише в пам'яті вкладки (без sessionStorage).
 * Раніше sessionStorage тримав старі каталоги/акції до 5 хв після видалення рядків у таблиці —
 * у клієнтів товари «не зникали». Після оновлення сторінки завжди йде свіжий запит до API.
 */
const memory = new Map<string, { exp: number; data: unknown }>();

function ttlMs(): number {
    if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_CLIENT_CACHE_TTL_MS) {
        const n = parseInt(process.env.NEXT_PUBLIC_API_CLIENT_CACHE_TTL_MS, 10);
        if (Number.isFinite(n) && n >= 0) return n;
    }
    return 120_000;
}

function safeKey(key: string): string {
    return key.length > 2000 ? key.slice(0, 2000) : key;
}

export function buildListCacheKey(path: string, params: Record<string, unknown>): string {
    const sorted: Record<string, unknown> = {};
    Object.keys(params)
        .sort()
        .forEach((k) => {
            sorted[k] = params[k];
        });
    return safeKey(`list:${path}:${JSON.stringify(sorted)}`);
}

export function readApiCache(key: string): unknown | null {
    const k = safeKey(key);
    const now = Date.now();
    const row = memory.get(k);
    if (row && row.exp > now) {
        return row.data;
    }
    return null;
}

export function writeApiCache(key: string, data: unknown): void {
    const k = safeKey(key);
    memory.set(k, { exp: Date.now() + ttlMs(), data });
}

/** Скинути кеш списків (наприклад після логіки «оновив каталог»). */
export function clearListApiCache(): void {
    memory.clear();
}
