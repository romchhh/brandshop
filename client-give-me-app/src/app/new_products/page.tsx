"use client";

import { Flex, List } from "antd";
import { Search } from "@/components/shared/Search";
import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import _ from "lodash";
import { emptyText } from "@/components/shared/EmptyText";
import { ProductPreview } from "@/components/shared/ProductPreview";
import classNames from "classnames";
import { API_HOST, LIST_PAGE_SIZE } from "@/lib/constants";
import { buildListCacheKey, readApiCache, writeApiCache } from "@/lib/apiCache";
import { beginPageWork } from "@/lib/pageWork";
import { Loader } from "@/components/shared/Loader";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";

const groupProduct = (products: any[]) => _.groupBy(products, "catalog_title");

function parsePageBody(data: unknown): { chunk: any[]; next: boolean } {
    if (Array.isArray(data)) {
        return { chunk: data, next: false };
    }
    const body = data as { results?: any[]; next?: boolean };
    return { chunk: body.results ?? [], next: !!body.next };
}

export default function NewProducts() {
    const [items, setItems] = useState<any[]>([]);
    const [searchQuery, setSearchQuery] = useState("");
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasNext, setHasNext] = useState(false);
    const pageRef = useRef(1);

    const fetchPage = useCallback(async (page: number, append: boolean) => {
        const params = { page, page_size: LIST_PAGE_SIZE };
        const cacheKey = buildListCacheKey("new-products", params);
        const hit = readApiCache(cacheKey);
        let data = hit;
        if (!data) {
            const res = await axios.get(`${API_HOST}/api/new-products/`, {
                headers: { "ngrok-skip-browser-warning": "test" },
                params,
            });
            data = res.data;
            writeApiCache(cacheKey, data);
        }
        const { chunk, next } = parsePageBody(data);
        setItems((prev) => (append ? [...prev, ...chunk] : chunk));
        setHasNext(next);
        pageRef.current = page;
    }, []);

    useEffect(() => {
        const finish = beginPageWork();
        fetchPage(1, false)
            .catch(() => {
                setItems([]);
                setHasNext(false);
            })
            .finally(() => {
                setLoading(false);
                finish();
            });
    }, [fetchPage]);

    const loadMore = useCallback(() => {
        if (!hasNext || loadingMore || loading) return;
        setLoadingMore(true);
        fetchPage(pageRef.current + 1, true).finally(() => setLoadingMore(false));
    }, [hasNext, loadingMore, loading, fetchPage]);

    const canLoadMore = hasNext && !loadingMore && !loading;
    const attachNewSentinel = useInfiniteScroll(loadMore, canLoadMore);

    const filtered = searchQuery.trim()
        ? items.filter((p) => p.title?.toLowerCase().includes(searchQuery.trim().toLowerCase()))
        : items;
    const groupedProducts = groupProduct(filtered);

    const onSearch = (event) => setSearchQuery(event.target.value);
    const onClearSearch = () => setSearchQuery("");

    if (loading && items.length === 0) {
        return <Loader />;
    }

    return (
        <>
            <Flex justify="center">
                <h1>Новинки</h1>
            </Flex>
            <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch} />
            {Object.entries(groupedProducts).map(([catalogTitle, groupProducts]) => (
                <div key={catalogTitle}>
                    <h2 style={{ margin: "24px 0 16px 0" }}>{catalogTitle}</h2>
                    <List
                        locale={{ emptyText }}
                        grid={{ gutter: 16, column: 2 }}
                        dataSource={groupProducts}
                        className={classNames("list-product-item")}
                        style={{ marginBottom: 20 }}
                        renderItem={(item, index) => (
                            <ProductPreview {...item} imagePriority={index < 2} />
                        )}
                    />
                </div>
            ))}
            {canLoadMore && (
                <div ref={attachNewSentinel} className="infinite-scroll-sentinel" style={{ height: 24, marginTop: 8 }} aria-hidden />
            )}
            {loadingMore && (
                <Flex justify="center" style={{ padding: 12 }}>
                    <Loader />
                </Flex>
            )}
        </>
    );
}