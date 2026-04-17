/**
 * Next.js Image optimizer тягне зображення з URL, який повертає API.
 * У Docker контейнер `client` не має Django на localhost:8000 — треба `http://server:8000`.
 * Задайте NEXT_PUBLIC_IMAGE_UPSTREAM при збірці образу (build args у docker-compose).
 */
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
    let fetchUrl = src;
    if (upstream && /^https?:\/\//i.test(src)) {
        fetchUrl = src
            .replace(/^http:\/\/localhost:8000\b/i, upstream)
            .replace(/^http:\/\/127\.0\.0\.1:8000\b/i, upstream)
            .replace(/^http:\/\/\[::1\]:8000\b/i, upstream);
    }
    const q = quality ?? 75;
    return `/_next/image?url=${encodeURIComponent(fetchUrl)}&w=${width}&q=${q}`;
}
