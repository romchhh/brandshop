import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

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
    }
    return NextResponse.next();
}

export const config = {
    matcher: ["/products/:path*"],
};
