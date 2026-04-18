/**
 * API часто віддає шлях з %D0%... (кирилиця в URL). Це нормально.
 * Інколи рядок уже «поламаний» (подвійне кодування) або WebView гірше їсть один варіант.
 * Нормалізуємо кожен сегмент pathname: decodeURIComponent → encodeURIComponent.
 */
function normalizeHttpUrlPathEncoding(href: string): string {
    try {
        const u = new URL(href);
        const segments = u.pathname.split("/").map((seg) => {
            if (!seg) return seg;
            try {
                return encodeURIComponent(decodeURIComponent(seg));
            } catch {
                return seg;
            }
        });
        u.pathname = segments.join("/");
        return u.toString();
    } catch {
        return href;
    }
}

function mediaSameOrigin(): boolean {
    return process.env.NEXT_PUBLIC_MEDIA_SAME_ORIGIN === '1' || process.env.NEXT_PUBLIC_MEDIA_SAME_ORIGIN === 'true';
}

/**
 * Якщо API повертає відносний шлях /media/... (Django без API_PUBLIC_URL),
 * браузер інакше звертається до Next, а не до бекенду — фото не грузиться.
 * Для шляхів з /public (/, /home.svg) префікс не додаємо.
 *
 * NEXT_PUBLIC_MEDIA_SAME_ORIGIN=1 — фото тільки як /media/... з поточного хосту Next (див. public/media
 * або volume server/media → public/media у Docker). Повні https://.../media/... з API перетворюються на шлях.
 */
export function resolveMediaSrc(src: string | null | undefined): string | null | undefined {
    if (src == null || src === '') {
        return src;
    }
    const s = String(src).trim();
    if (/^(https?:|data:|blob:)/i.test(s)) {
        if (/^https?:/i.test(s)) {
            if (mediaSameOrigin()) {
                try {
                    const u = new URL(s);
                    if (u.pathname.startsWith('/media/')) {
                        return normalizeHttpUrlPathEncoding(u.pathname + u.search);
                    }
                } catch {
                    /* fall through */
                }
            }
            return normalizeHttpUrlPathEncoding(s);
        }
        return s;
    }
    // Відносний протокол від CDN/API
    if (s.startsWith('//') && s.includes('media')) {
        return normalizeHttpUrlPathEncoding(`https:${s}`);
    }
    if (s.startsWith('/media/')) {
        if (mediaSameOrigin()) {
            return normalizeHttpUrlPathEncoding(s);
        }
        const base = (process.env.NEXT_PUBLIC_API_HOST || '').trim().replace(/\/$/, '');
        if (base) {
            return normalizeHttpUrlPathEncoding(`${base}${s}`);
        }
    }
    return s;
}
