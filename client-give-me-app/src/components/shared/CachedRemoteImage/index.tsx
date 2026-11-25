"use client";

import Image, { type ImageProps } from "next/image";

import { resolveMediaSrc } from "@/lib/resolveMediaSrc";

function isRemoteAbsoluteUrl(src: string): boolean {
    return /^https?:\/\//i.test(src.trim());
}

export function isNonRasterImageSrc(src: string): boolean {
    const base = src.split("?")[0].toLowerCase();
    return (
        base.endsWith(".svg") ||
        src.startsWith("data:") ||
        src.startsWith("blob:")
    );
}

export type CachedRemoteImageProps = Omit<ImageProps, "src"> & {
    src: string | null | undefined;
};

/**
 * SVG / data / blob / зовнішні absolute URL — без /_next/image.
 * Відносні /media/... (same-origin volume) — через оптимізатор Next (webp/avif, менший трафік).
 */
export function CachedRemoteImage({
    src,
    alt = "",
    unoptimized,
    priority,
    loading,
    sizes,
    ...rest
}: CachedRemoteImageProps) {
    if (!src) {
        return null;
    }
    const resolved = resolveMediaSrc(src) ?? src;
    const sameOriginMedia = resolved.startsWith("/media/");
    const autoUnopt =
        unoptimized ??
        (isNonRasterImageSrc(resolved) ||
            (isRemoteAbsoluteUrl(resolved) && !sameOriginMedia));

    return (
        <Image
            src={resolved}
            alt={alt}
            unoptimized={autoUnopt}
            sizes={sizes ?? (sameOriginMedia ? "(max-width: 768px) 50vw, 240px" : undefined)}
            {...rest}
            {...(priority
                ? { priority: true as const }
                : { loading: (loading ?? "lazy") as "lazy" | "eager" })}
        />
    );
}
