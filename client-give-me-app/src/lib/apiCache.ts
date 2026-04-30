/**
 * Кеш GET-відповідей у пам'яті + sessionStorage (переживає soft reload).
 * Зменшує повторні запити до API для каталогу / акцій.
 */
const memory = new Map<string, { exp: number; data: unknown }>();

function ttlMs(): number {
    if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_CLIENT_CACHE_TTL_MS) {
        const n = parseInt(process.env.NEXT_PUBLIC_API_CLIENT_CACHE_TTL_MS, 10);
        if (Number.isFinite(n) && n >= 0) return n;
    }
    return 300_000;
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
    if (typeof window !== "undefined") {
        try {
            const raw = sessionStorage.getItem(k);
            if (!raw) return null;
            const parsed = JSON.parse(raw) as { exp: number; data: unknown };
            if (typeof parsed.exp === "number" && parsed.exp > now) {
                memory.set(k, { exp: parsed.exp, data: parsed.data });
                return parsed.data;
            }
            sessionStorage.removeItem(k);
        } catch {
            /* ignore */
        }
    }
    return null;
}

export function writeApiCache(key: string, data: unknown): void {
    const k = safeKey(key);
    const exp = Date.now() + ttlMs();
    memory.set(k, { exp, data });
    if (typeof window !== "undefined") {
        try {
            sessionStorage.setItem(k, JSON.stringify({ exp, data }));
        } catch {
            /* quota — лишаємо лише memory */
        }
    }
}
