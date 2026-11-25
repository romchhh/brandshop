import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Без зайвих логів і фонових API-запитів — менше навантаження на CPU/мережу. */
export function middleware(_request: NextRequest) {
    return NextResponse.next();
}

export const config = {
    matcher: [],
};
