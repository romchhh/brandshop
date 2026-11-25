"use client";

import { Flex, List } from "antd";
import { Search } from "@/components/shared/Search";
import { useSelector } from "react-redux";
import { RootState } from "@/store/store";
import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { ProductPreview } from "@/components/shared/ProductPreview";
import { emptyText } from "@/components/shared/EmptyText";
import classNames from "classnames";
import { API_HOST, LIST_PAGE_SIZE } from "@/lib/constants";
import { buildListCacheKey, readApiCache, writeApiCache } from "@/lib/apiCache";
import { beginPageWork } from "@/lib/pageWork";
import { Loader } from "@/components/shared/Loader";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";

function FavoritesPage() {
    const favoriteIds = useSelector((state: RootState) => state.favorite.items);
    const [allProducts, setAllProducts] = useState<any[]>([]);
    const [favoriteProducts, setFavoriteProducts] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasNext, setHasNext] = useState(false);
    const offsetRef = useRef(0);
    const idsKeyRef = useRef("");
    const sentinelRef = useRef<HTMLDivElement>(null);

    const loadChunk = useCallback(
        async (offset: number, append: boolean, ids: string) => {
            const params = { ids, offset, limit: LIST_PAGE_SIZE };
            const cacheKey = buildListCacheKey("products-by-ids", params);
            const cached = readApiCache(cacheKey);
            let data = cached;
            if (!data) {
                const res = await axios.get(`${API_HOST}/api/products/by-ids/`, {
                    params,
                    headers: { "ngrok-skip-browser-warning": "test" },
                });
                data = res.data;
                writeApiCache(cacheKey, data);
            }
            const body = Array.isArray(data) ? { results: data, next: false } : data;
            const chunk = body.results ?? [];
            const next = !!body.next;
            setAllProducts((prev) => (append ? [...prev, ...chunk] : chunk));
            setFavoriteProducts((prev) => (append ? [...prev, ...chunk] : chunk));
            setHasNext(next);
            offsetRef.current = offset + chunk.length;
        },
        [],
    );

    useEffect(() => {
        if (favoriteIds.length === 0) {
            setAllProducts([]);
            setFavoriteProducts([]);
            setHasNext(false);
            idsKeyRef.current = "";
            return;
        }
        const ids = favoriteIds.join(",");
        if (idsKeyRef.current !== ids) {
            idsKeyRef.current = ids;
            offsetRef.current = 0;
        }
        setLoading(true);
        const finish = beginPageWork();
        loadChunk(0, false, ids)
            .catch(() => {
                setAllProducts([]);
                setFavoriteProducts([]);
                setHasNext(false);
            })
            .finally(() => {
                setLoading(false);
                finish();
            });
    }, [favoriteIds, loadChunk]);

    const loadMore = useCallback(() => {
        if (!hasNext || loadingMore || loading || !idsKeyRef.current) return;
        setLoadingMore(true);
        loadChunk(offsetRef.current, true, idsKeyRef.current).finally(() => setLoadingMore(false));
    }, [hasNext, loadingMore, loading, loadChunk]);

    useInfiniteScroll(sentinelRef, loadMore, hasNext && !loadingMore && !loading);

    const onSearch = (event) => {
        const value = event.target.value.toLowerCase();
        setFavoriteProducts(allProducts.filter((product) => product.title?.toLowerCase().includes(value)));
    };

    const onClearSearch = () => {
        setFavoriteProducts(allProducts);
    };

    if (loading && favoriteProducts.length === 0) {
        return <Loader />;
    }

    return (
        <>
            <Flex justify="center">
                <h1>Обране</h1>
            </Flex>
            <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch} />
            <List
                locale={{ emptyText }}
                grid={{ gutter: 16, column: 2 }}
                dataSource={favoriteProducts}
                className={classNames("list-product-item")}
                style={{ marginTop: 20 }}
                renderItem={(item, index) => <ProductPreview {...item} imagePriority={index < 2} />}
            />
            {hasNext && <div ref={sentinelRef} style={{ height: 1, marginTop: 8 }} aria-hidden />}
            {loadingMore && (
                <Flex justify="center" style={{ padding: 12 }}>
                    <Loader />
                </Flex>
            )}
        </>
    );
}

export default FavoritesPage;