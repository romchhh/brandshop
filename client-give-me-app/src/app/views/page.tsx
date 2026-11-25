"use client";

import { Flex, List } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useInitData } from "@telegram-apps/sdk-react";

import { Search } from "@/components/shared/Search";
import { RootState } from "@/store/store";
import { fetchViewProductsRequest } from "@/store/productSlice";
import { emptyText } from "@/components/shared/EmptyText";
import { ProductPreview } from "@/components/shared/ProductPreview";
import { getUserId } from "@/lib/helpers";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import { Loader } from "@/components/shared/Loader";

export default function Views() {
    const dispatch = useDispatch();
    const products = useSelector((state: RootState) => state.product.viewProducts);
    const hasNext = useSelector((state: RootState) => state.product.viewProductsHasNext);
    const loadingMore = useSelector((state: RootState) => state.product.viewProductsLoadingMore);
    const isLoading = useSelector((state: RootState) => state.product.loading);
    const [resultProducts, setResultProducts] = useState<any[] | null>(null);
    const initData = useInitData(true);
    const pageRef = useRef(1);
    const sentinelRef = useRef<HTMLDivElement>(null);

    const userId = initData ? getUserId(initData) : null;

    useEffect(() => {
        if (!userId) return;
        pageRef.current = 1;
        dispatch(fetchViewProductsRequest({ userId, page: 1, append: false }));
    }, [userId, dispatch]);

    const loadMore = useCallback(() => {
        if (!userId || !hasNext || loadingMore || isLoading) return;
        const next = pageRef.current + 1;
        pageRef.current = next;
        dispatch(fetchViewProductsRequest({ userId, page: next, append: true }));
    }, [userId, hasNext, loadingMore, isLoading, dispatch]);

    useInfiniteScroll(sentinelRef, loadMore, !!hasNext && !loadingMore && !isLoading);

    const onSearch = (event) => {
        const value = event.target.value;
        setResultProducts(
            products.filter((product) => product.title.toLowerCase().includes(value.toLowerCase())),
        );
    };
    const onClearSearch = () => {
        setResultProducts(products);
    };

    useEffect(() => {
        setResultProducts(products);
    }, [products]);

    return (
        <>
            <Flex justify="center">
                <h1>Переглянуті товари</h1>
            </Flex>
            <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch} />
            {isLoading && !resultProducts?.length && <Loader />}
            {resultProducts && (
                <List
                    locale={{ emptyText }}
                    grid={{ gutter: 16, column: 2 }}
                    dataSource={resultProducts}
                    style={{ marginTop: 20 }}
                    renderItem={(item) => <ProductPreview {...item} />}
                />
            )}
            {hasNext && <div ref={sentinelRef} style={{ height: 1, marginTop: 8 }} aria-hidden />}
            {loadingMore && (
                <Flex justify="center" style={{ padding: 12 }}>
                    <Loader />
                </Flex>
            )}
        </>
    );
}