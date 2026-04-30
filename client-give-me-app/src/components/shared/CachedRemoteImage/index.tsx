"use client";

import Image, { type ImageProps } from "next/image";

import { resolveMediaSrc } from "@/lib/resolveMediaSrc";

/** Фото з Django (/media/...) як повний http(s) — тягнути напряму в <img>, без /_next/image (у Telegram WebView часто ламається оптимізатор). */
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
 * SVG / data / blob — без оптимізації.
 * Повні http(s) URL (медіа з API) — без /_next/image, щоб міні-ап і прод не ламалися на fetch з боку Next.
 * За замовчуванням loading="lazy", якщо не передано priority.
 */
export function CachedRemoteImage({
    src,
    alt = "",
    unoptimized,
    priority,
    loading,
    ...rest
}: CachedRemoteImageProps) {
    if (!src) {
        return null;
    }
    const resolved = resolveMediaSrc(src) ?? src;
    const autoUnopt =
        isNonRasterImageSrc(resolved) ||
        isRemoteAbsoluteUrl(resolved) ||
        resolved.startsWith("/media/");
    return (
        <Image
            src={resolved}
            alt={alt}
            unoptimized={unoptimized ?? autoUnopt}
            {...rest}
            {...(priority ? { priority: true as const } : { loading: (loading ?? "lazy") as "lazy" | "eager" })}
        />
    );
}
