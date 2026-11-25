import { useEffect, type RefObject } from "react";

/** Викликає onLoadMore, коли sentinel потрапляє у видиму область (з запасом 240px). */
export function useInfiniteScroll(
    sentinelRef: RefObject<HTMLElement | null>,
    onLoadMore: () => void,
    enabled: boolean,
) {
    useEffect(() => {
        if (!enabled) return;
        const el = sentinelRef.current;
        if (!el) return;
        const obs = new IntersectionObserver(
            (entries) => {
                if (entries[0]?.isIntersecting) onLoadMore();
            },
            { rootMargin: "240px", threshold: 0 },
        );
        obs.observe(el);
        return () => obs.disconnect();
    }, [enabled, onLoadMore, sentinelRef]);
}