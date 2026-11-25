let pending = 0;

/** Позначає локальне завантаження сторінки, якого немає в Redux. */
export function beginPageWork(): () => void {
    pending += 1;
    let closed = false;
    return () => {
        if (closed) return;
        closed = true;
        pending = Math.max(0, pending - 1);
    };
}

export function pageWorkPending(): boolean {
    return pending > 0;
}
