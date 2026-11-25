import { useEffect, useRef, useState } from "react";

function findScrollRoot(el: HTMLElement): Element | null {
    let node: HTMLElement | null = el.parentElement;
    while (node && node !== document.body) {
        const oy = getComputedStyle(node).overflowY;
        if (/(auto|scroll|overlay)/.test(oy) && node.scrollHeight > node.clientHeight + 2) {
            return node;
        }
        node = node.parentElement;
    }
    return null;
}

function isNearBottom(root: Element | null, marginPx: number): boolean {
    if (root) {
        return root.scrollHeight - root.scrollTop - root.clientHeight < marginPx;
    }
    return (
        document.documentElement.scrollHeight - window.scrollY - window.innerHeight < marginPx
    );
}

/** Підвантаження при доскролі. Повертає callback-ref для sentinel-елемента. */
export function useInfiniteScroll(onLoadMore: () => void, enabled: boolean) {
    const [sentinel, setSentinel] = useState<HTMLElement | null>(null);
    const onLoadMoreRef = useRef(onLoadMore);
    onLoadMoreRef.current = onLoadMore;
    const busyRef = useRef(false);

    useEffect(() => {
        if (!enabled || !sentinel) return;

        const triggerLoad = () => {
            if (busyRef.current) return;
            busyRef.current = true;
            onLoadMoreRef.current();
            window.setTimeout(() => {
                busyRef.current = false;
            }, 350);
        };

        const root = findScrollRoot(sentinel);
        const obs = new IntersectionObserver(
            (entries) => {
                if (entries.some((e) => e.isIntersecting)) triggerLoad();
            },
            { root, rootMargin: "480px 0px 240px", threshold: 0 },
        );
        obs.observe(sentinel);

        const onScroll = () => {
            if (isNearBottom(root, 480)) triggerLoad();
        };
        const scrollTarget: EventTarget = root ?? window;
        scrollTarget.addEventListener("scroll", onScroll, { passive: true });

        requestAnimationFrame(() => {
            const rect = sentinel.getBoundingClientRect();
            const inView = rect.top < window.innerHeight + 400;
            if (inView || isNearBottom(root, 520)) triggerLoad();
        });

        return () => {
            obs.disconnect();
            scrollTarget.removeEventListener("scroll", onScroll);
        };
    }, [enabled, sentinel]);

    return setSentinel;
}