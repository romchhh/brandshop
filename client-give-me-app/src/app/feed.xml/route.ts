import { NextResponse } from "next/server";

/** Django віддає фід; на домені магазину проксуємо сюди. */
function feedUpstreamBase(): string {
    const internal = (process.env.NEXT_PUBLIC_IMAGE_UPSTREAM || process.env.SERVER_URL || "").trim().replace(
        /\/$/,
        "",
    );
    if (internal) return internal;
    const pub = (process.env.NEXT_PUBLIC_API_HOST || "").trim().replace(/\/$/, "");
    return pub;
}

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
    const base = feedUpstreamBase();
    if (!base) {
        return NextResponse.json({ error: "API upstream not configured" }, { status: 503 });
    }
    const url = `${base}/feed.xml`;
    try {
        const res = await fetch(url, {
            headers: { Accept: "application/xml" },
            cache: "no-store",
        });
        if (!res.ok) {
            return NextResponse.json(
                { error: `Feed upstream ${res.status}` },
                { status: res.status === 404 ? 502 : res.status },
            );
        }
        const body = await res.arrayBuffer();
        const headers = new Headers({
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=120, must-revalidate",
        });
        const lm = res.headers.get("Last-Modified");
        if (lm) headers.set("Last-Modified", lm);
        return new NextResponse(body, { status: 200, headers });
    } catch {
        return NextResponse.json({ error: "Feed fetch failed" }, { status: 502 });
    }
}