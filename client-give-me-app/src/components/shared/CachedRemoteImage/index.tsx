"use client";

import Image, { type ImageProps } from "next/image";

import { resolveMediaSrc } from "@/lib/resolveMediaSrc";

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
 * Remote photos go through the Next.js image optimizer (WebP/AVIF, resized, HTTP cache).
 * SVG / data / blob URLs stay unoptimized (native delivery).
 */
export function CachedRemoteImage({
    src,
    alt = "",
    unoptimized,
    ...rest
}: CachedRemoteImageProps) {
    if (!src) {
        return null;
    }
    const resolved = resolveMediaSrc(src) ?? src;
    return (
        <Image
            src={resolved}
            alt={alt}
            unoptimized={unoptimized ?? isNonRasterImageSrc(src)}
            {...rest}
        />
    );
}
