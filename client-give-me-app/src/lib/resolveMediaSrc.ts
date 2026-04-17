/**
 * Якщо API повертає відносний шлях /media/... (Django без API_PUBLIC_URL),
 * браузер інакше звертається до Next, а не до бекенду — фото не грузиться.
 * Для шляхів з /public (/, /home.svg) префікс не додаємо.
 */
export function resolveMediaSrc(src: string | null | undefined): string | null | undefined {
    if (src == null || src === '') {
        return src;
    }
    const s = String(src).trim();
    if (/^(https?:|data:|blob:)/i.test(s)) {
        return s;
    }
    if (s.startsWith('/media/')) {
        const base = (process.env.NEXT_PUBLIC_API_HOST || '').trim().replace(/\/$/, '');
        if (base) {
            return `${base}${s}`;
        }
    }
    return s;
}
