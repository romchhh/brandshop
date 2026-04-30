"use client";

import { Button, Flex, List, Space, Select } from "antd";
import { Search } from "@/components/shared/Search";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/store/store";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMount } from "react-use";
import { emptyText } from "@/components/shared/EmptyText";
import { fetchPromotionalProductsRequest } from "@/store/productSlice";
import _ from "lodash";
import classNames from "classnames";

import "./index.css";
import { ProductPreview } from "@/components/shared/ProductPreview";

const groupProduct = (products: any[]) => _.groupBy(products, "catalog_title");

export default function PromotionalOffers() {
    const dispatch = useDispatch();
    const products = useSelector((state: RootState) => state.product.promotionalProducts);
    const promotionalProductsHasNext = useSelector(
        (state: RootState) => state.product.promotionalProductsHasNext,
    );
    const promotionalLoadingMore = useSelector(
        (state: RootState) => state.product.promotionalLoadingMore,
    );
    const isLoading = useSelector((state: RootState) => state.product.loading);
    const [groupedProducts, setGroupedProducts] = useState<Record<string, any[]> | null>(null);
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
    const lastLoadedPageRef = useRef(1);

    const productOrderIndex = useMemo(() => {
        const m = new Map<number, number>();
        (products || []).forEach((p, i) => m.set(p.id, i));
        return m;
    }, [products]);

    const onSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
        const value = event.target.value;
        filterProducts(value, selectedCategory);
    };

    const onClearSearch = () => {
        filterProducts("", selectedCategory);
    };

    const onCategoryChange = (value: string | null) => {
        setSelectedCategory(value);
        filterProducts("", value);
    };

    const filterProducts = (searchValue: string, category: string | null) => {
        let filteredProducts = products;

        if (searchValue) {
            filteredProducts = filteredProducts.filter((product) =>
                product.title.toLowerCase().includes(searchValue.toLowerCase()),
            );
        }

        if (category) {
            filteredProducts = filteredProducts.filter((product) => product.catalog_title === category);
        }

        setGroupedProducts(groupProduct(filteredProducts));
    };

    const categories = products?.length
        ? [{ label: "Всі категорії", value: null }].concat(
              [...new Set(products.map((product) => product.catalog_title))].map((category) => ({
                  label: category,
                  value: category,
              })),
          )
        : [];

    useMount(() => {
        lastLoadedPageRef.current = 1;
        dispatch(fetchPromotionalProductsRequest({ page: 1, append: false } as any));
    });

    useEffect(() => {
        setGroupedProducts(groupProduct(products || []));
    }, [products]);

    const loadMore = useCallback(() => {
        if (!promotionalProductsHasNext || promotionalLoadingMore || isLoading) return;
        const next = lastLoadedPageRef.current + 1;
        lastLoadedPageRef.current = next;
        dispatch(fetchPromotionalProductsRequest({ page: next, append: true } as any));
    }, [promotionalProductsHasNext, promotionalLoadingMore, isLoading, dispatch]);

    return (
        <>
            <Flex justify="center">
                <h1>Акційні пропозиції</h1>
            </Flex>
            <Space direction="vertical" style={{ width: "100%" }}>
                <Search placeholder="Пошук товару" handler={onSearch} onClearSearch={onClearSearch} />
                <Select
                    style={{ width: "200px" }}
                    placeholder="Оберіть категорію"
                    value={selectedCategory}
                    onChange={onCategoryChange}
                    options={categories}
                    allowClear
                />
            </Space>
            {groupedProducts &&
                Object.entries(groupedProducts).map(([catalogTitle, groupProducts]) => (
                    <div key={catalogTitle}>
                        <h2 style={{ margin: "24px 0 16px 0" }}>{catalogTitle}</h2>
                        <List
                            locale={{ emptyText }}
                            grid={{ gutter: 16, column: 2 }}
                            dataSource={groupProducts}
                            className={classNames("list-product-item")}
                            style={{ marginBottom: 20 }}
                            renderItem={(item) => (
                                <ProductPreview
                                    {...item}
                                    imagePriority={(productOrderIndex.get(item.id) ?? 0) < 20}
                                />
                            )}
                        />
                    </div>
                ))}
            {promotionalProductsHasNext && (
                <Flex justify="center" style={{ marginTop: 16 }}>
                    <Button type="default" onClick={loadMore} loading={promotionalLoadingMore} block>
                        Показати ще
                    </Button>
                </Flex>
            )}
        </>
    );
}
