"use client";

import { useEffect, useRef, useState } from "react";
import { Spin } from "antd";
import { usePathname } from "next/navigation";
import { store } from "@/store/store";
import { pageWorkPending } from "@/lib/pageWork";

const MIN_VISIBLE_MS = 280;
const MAX_VISIBLE_MS = 12000;

function dataStillLoading() {
    const state = store.getState();
    const catalogBusy = state.catalog.loading && state.catalog.catalogs.length === 0;
    const productBusy =
        state.product.loading &&
        !state.product.product &&
        !(state.product.promotionalProducts?.length) &&
        !(state.product.viewProducts?.length);
    return catalogBusy || productBusy || state.basketItem.loading || state.order.loading || pageWorkPending();
}

export function PageEnterLoader() {
    const pathname = usePathname();
    const pathnameRef = useRef(pathname);
    pathnameRef.current = pathname;
    const [visible, setVisible] = useState(true);

    useEffect(() => {
        let cancelHide = 0;

        const show = () => {
            setVisible(true);
            const from = pathnameRef.current;
            window.clearTimeout(cancelHide);
            cancelHide = window.setTimeout(() => {
                if (pathnameRef.current === from && !dataStillLoading()) setVisible(false);
            }, 1500);
        };

        const showIfOtherPath = (url?: string | URL | null) => {
            if (url == null || url === "") return;
            try {
                const next = new URL(String(url), window.location.origin).pathname;
                if (next !== pathnameRef.current) show();
            } catch {
                /* некоректне посилання */
            }
        };

        const originalPush = window.history.pushState.bind(window.history);
        const originalReplace = window.history.replaceState.bind(window.history);
        window.history.pushState = (data, unused, url) => {
            showIfOtherPath(url);
            return originalPush(data, unused, url);
        };
        window.history.replaceState = (data, unused, url) => {
            showIfOtherPath(url);
            return originalReplace(data, unused, url);
        };

        const onClick = (event: MouseEvent) => {
            if (
                event.defaultPrevented ||
                event.button !== 0 ||
                event.metaKey ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey
            ) {
                return;
            }
            const target = event.target as HTMLElement | null;
            if (target?.closest(".favorite-button")) return;
            const anchor = target?.closest?.("a");
            if (anchor && anchor.target !== "_blank") {
                const href = anchor.getAttribute("href");
                if (href && !href.startsWith("#")) showIfOtherPath(href);
                return;
            }
            if (target?.closest(".nav-item, .category-item, .product-item-preview, .ant-menu-item, .back-button-container")) {
                show();
            }
        };

        const onPop = () => show();
        document.addEventListener("click", onClick, true);
        window.addEventListener("popstate", onPop);
        return () => {
            window.clearTimeout(cancelHide);
            window.history.pushState = originalPush;
            window.history.replaceState = originalReplace;
            document.removeEventListener("click", onClick, true);
            window.removeEventListener("popstate", onPop);
        };
    }, []);

    useEffect(() => {
        setVisible(true);
        const started = Date.now();
        let timer = 0;
        const tick = () => {
            const waited = Date.now() - started;
            const busy = dataStillLoading();
            if ((busy && waited < MAX_VISIBLE_MS) || waited < MIN_VISIBLE_MS) {
                timer = window.setTimeout(tick, busy ? 80 : Math.max(MIN_VISIBLE_MS - waited, 16));
                return;
            }
            setVisible(false);
        };
        timer = window.setTimeout(tick, 40);
        return () => window.clearTimeout(timer);
    }, [pathname]);

    if (!visible) return null;

    return (
        <div className="page-enter-loader" role="status" aria-live="polite" aria-label="Завантаження">
            <Spin size="large" />
        </div>
    );
}
