/**
 * Next.js Image optimizer тягне зображення з URL з API.
 * - У Docker: якщо в JSON повний публічний URL API — підміняємо на http://server:8000 для fetch з контейнера client.
 * - localhost:8000 у JSON також підміняється на upstream.
 * Збірка: NEXT_PUBLIC_API_HOST, NEXT_PUBLIC_IMAGE_UPSTREAM (docker-compose).
 */
function trimBase(url: string): string {
    return url.trim().replace(/\/$/, '');
}

export default function imageLoader({
    src,
    width,
    quality,
}: {
    src: string;
    width: number;
    quality?: number;
}): string {
    const upstream = process.env.NEXT_PUBLIC_IMAGE_UPSTREAM?.trim();
    const publicApi = process.env.NEXT_PUBLIC_API_HOST?.trim()
        ? trimBase(process.env.NEXT_PUBLIC_API_HOST as string)
        : '';

    let fetchUrl = src;
    if (upstream && /^https?:\/\//i.test(src)) {
        if (publicApi && src.startsWith(publicApi)) {
            fetchUrl = upstream + src.slice(publicApi.length);
        } else {
            fetchUrl = src
                .replace(/^http:\/\/localhost:8000\b/i, upstream)
                .replace(/^http:\/\/127\.0\.0\.1:8000\b/i, upstream)
                .replace(/^http:\/\/\[::1\]:8000\b/i, upstream);
        }
    }
    const q = quality ?? 75;
    return `/_next/image?url=${encodeURIComponent(fetchUrl)}&w=${width}&q=${q}`;
}
