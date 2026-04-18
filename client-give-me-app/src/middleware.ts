import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

type ProductApiPayload = {
    photo?: string | null;
    title?: string;
    product_properties?: Array<{ id: number; title?: string; photo?: string | null }>;
};

/**
 * Той самий JSON, що й у браузері з GET /api/products/:id — лог у stdout Docker (фото з Django).
 * Не блокує відповідь сторінки (fetch після return не чекаємо в критичному шляху — ok, ми одразу return next).
 */
function logProductPhotoFromApi(apiBase: string, productId: string): void {
    const base = apiBase.replace(/\/$/, "");
    const url = `${base}/api/products/${productId}`;
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), 8000);
    fetch(url, {
        signal: ac.signal,
        headers: { Accept: "application/json" },
    })
        .finally(() => clearTimeout(timer))
        .then((res) => {
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            return res.json() as Promise<ProductApiPayload>;
        })
        .then((data) => {
            console.log(
                JSON.stringify({
                    tag: "[BrandShop]",
                    event: "product_api_photo",
                    productId,
                    apiUrl: url,
                    title: data.title ?? null,
                    photo: data.photo ?? null,
                    product_properties_photos:
                        data.product_properties?.map((p) => ({
                            id: p.id,
                            title: p.title,
                            photo: p.photo ?? null,
                        })) ?? [],
                })
            );
        })
        .catch((err: unknown) => {
            console.error(
                JSON.stringify({
                    tag: "[BrandShop]",
                    event: "product_api_photo_error",
                    productId,
                    apiUrl: url,
                    error: err instanceof Error ? err.message : String(err),
                })
            );
        });
}

/**
 * Логи в stdout контейнера client (docker compose logs -f client) при відкритті /products/:id
 * Клієнтські console.log з page.tsx сюди не потрапляють — лише цей серверний шар.
 */
export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;
    const match = pathname.match(/^\/products\/([^/]+)\/?$/);
    if (match) {
        const productId = match[1];
        const line = {
            tag: "[BrandShop]",
            event: "product_page_request",
            productId,
            pathname,
            method: request.method,
            NEXT_PUBLIC_API_HOST: process.env.NEXT_PUBLIC_API_HOST || null,
            ts: new Date().toISOString(),
        };
        console.log(JSON.stringify(line));

        const apiBase = process.env.NEXT_PUBLIC_API_HOST?.trim();
        if (apiBase) {
            logProductPhotoFromApi(apiBase, productId);
        } else {
            console.warn(
                JSON.stringify({
                    tag: "[BrandShop]",
                    event: "product_api_photo_skip",
                    reason: "NEXT_PUBLIC_API_HOST порожній — немає бази для запиту до Django",
                    productId,
                })
            );
        }
    }
    return NextResponse.next();
}

export const config = {
    matcher: ["/products/:path*"],
};
