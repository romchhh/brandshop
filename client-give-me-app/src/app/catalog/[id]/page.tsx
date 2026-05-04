"use client";

import { Search } from "@/components/shared/Search";
import { Space, Flex, List, Row, Col, Select, InputNumber, Button } from 'antd';
import Image from "next/image";
import { useDispatch, useSelector } from "react-redux";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import './index.css'
import classNames from "classnames";

import { emptyText } from "@/components/shared/EmptyText";
import { ProductPreview } from "@/components/shared/ProductPreview";
import { fetchCatalogRequest, resetCatalog } from "@/store/catalogSlice";
import { RootState } from "@/store/store";
import { BackButton } from "@/components/shared/BackButton";
import { Loader } from "@/components/shared/Loader";
import { getCatalogSizeFilterOptions, propertyTitleMatchesSize } from "@/config/catalogs";

export default function CatalogItem({ params: { id } }) {
    const dispatch = useDispatch();
    const catalog = useSelector((state: RootState) => state.catalog.catalog);
    const [resultCatalog, setResultCatalog] = useState(null);
    const [selectedSize, setSelectedSize] = useState(null);
    const [minPrice, setMinPrice] = useState(null);
    const [maxPrice, setMaxPrice] = useState(null);
    const [searchValue, setSearchValue] = useState('');
    const isLoading = useSelector((state: RootState) => state.catalog.loading);
    const catalogLoadingMore = useSelector((state: RootState) => state.catalog.catalogLoadingMore);
    const catalogProductsHasNext = useSelector((state: RootState) => state.catalog.catalogProductsHasNext);
    const lastLoadedPageRef = useRef(1);

    const sizeFilterOptions = useMemo(
        () => getCatalogSizeFilterOptions(catalog?.title, catalog?.products || []),
        [catalog?.title, catalog?.products],
    );

    useEffect(() => {
        lastLoadedPageRef.current = 1;
        dispatch(fetchCatalogRequest({ id, page: 1, append: false }));
        if (typeof window !== "undefined") {
            const savedFilters = localStorage.getItem(`catalog-${id}-filters`);
            if (savedFilters) {
                const { size, min, max, search } = JSON.parse(savedFilters);
                setSelectedSize(size);
                setMinPrice(min);
                setMaxPrice(max);
                setSearchValue(search);
            }
        }
    }, [id, dispatch]);

    const loadMoreCatalog = useCallback(() => {
        if (!catalogProductsHasNext || catalogLoadingMore || isLoading) return;
        const next = lastLoadedPageRef.current + 1;
        lastLoadedPageRef.current = next;
        dispatch(fetchCatalogRequest({ id, page: next, append: true }));
    }, [catalogProductsHasNext, catalogLoadingMore, isLoading, dispatch, id]);

    // Зберігаємо фільтри при розмонтуванні
    useEffect(() => {
        return () => {
            if (typeof window !== "undefined") {
                if (window.location.pathname.includes('/products/')) {
                    const filters = {
                        size: selectedSize,
                        min: minPrice,
                        max: maxPrice,
                        search: searchValue
                    };
                    localStorage.setItem(`catalog-${id}-filters`, JSON.stringify(filters));
                } else {
                    localStorage.removeItem(`catalog-${id}-filters`);
                }
            }
        };
    }, [id, selectedSize, minPrice, maxPrice, searchValue]);

    const onSearch = (event) => {
        const value = event.target.value;
        setSearchValue(value);
        const list = catalog?.products || [];
        setResultCatalog({
            ...catalog,
            products: list.filter((p) => p.title.toLowerCase().includes(value.toLowerCase())),
        });
    };

    const onClearSearch = () => {
        setSearchValue('');
        setResultCatalog(catalog);
    };

    const onSizeChange = (size) => {
        setSelectedSize(size);
    };

    const onMinPriceChange = (value) => {
        setMinPrice(value);
    };

    const onMaxPriceChange = (value) => {
        setMaxPrice(value);
    };

    useEffect(() => {
        setResultCatalog(catalog);
    }, [catalog]);

    useEffect(() => {
        if (catalog && catalog.products) {
            let filteredProducts = catalog.products;

            // Фільтрація за розміром
            if (selectedSize) {
                filteredProducts = filteredProducts.filter((product) =>
                    product.product_properties?.some((property) =>
                        propertyTitleMatchesSize(property.title, selectedSize)
                    )
                );
            }

            // Фільтрація за ціною
            if (minPrice !== null || maxPrice !== null) {
                filteredProducts = filteredProducts.filter((product) => {
                    const price = product.promotional_price || product.price;
                    return (
                        (minPrice === null || price >= minPrice) &&
                        (maxPrice === null || price <= maxPrice)
                    );
                });
            }

            setResultCatalog({ ...catalog, products: filteredProducts });
        }
    }, [selectedSize, minPrice, maxPrice, catalog]);

    return (
        <Space.Compact block direction="vertical">
            <Row>
                <Col span={2}>
                    <Flex align="center" style={{ height: '100%' }}>
                        <BackButton />
                    </Flex>
                </Col>
                <Col span={20}>
                    <Flex justify="center" style={{ width: '100%' }}>
                        {resultCatalog?.title ? <h1>{resultCatalog.title}</h1> : <h1>Завантаження...</h1>}
                    </Flex>
                </Col>
            </Row>
            {isLoading && <Loader />}
            {!isLoading && resultCatalog && (
                <>
                    <Search 
                        placeholder="Пошук..." 
                        handler={onSearch} 
                        onClear={onClearSearch}
                        value={searchValue} 
                    />
                    <Flex justify="center" style={{ margin: '16px 0', gap: '8px', alignItems: 'center' }}>
                        {sizeFilterOptions.length > 0 && (
                            <Select
                                value={selectedSize}
                                placeholder="Розмір"
                                options={sizeFilterOptions}
                                onChange={onSizeChange}
                                allowClear
                                showSearch
                                optionFilterProp="label"
                                style={{ width: 140 }}
                            />
                        )}
                        <InputNumber
                            value={minPrice}
                            placeholder="Від"
                            min={0}
                            onChange={onMinPriceChange}
                            style={{ width: 100 }}
                        />
                        <InputNumber
                            value={maxPrice}
                            placeholder="До"
                            min={0}
                            onChange={onMaxPriceChange}
                            style={{ width: 100 }}
                        />
                    </Flex>
                    <List
                        locale={{ emptyText }}
                        grid={{ gutter: 16, column: 2 }}
                        className={classNames("list-product-item")}
                        dataSource={resultCatalog.products}
                        renderItem={(item, index) => (
                            <ProductPreview
                                catalogTitle={resultCatalog.title}
                                {...item}
                                imagePriority={index < 20}
                            />
                        )}
                    />
                    {catalogProductsHasNext && (
                        <Flex justify="center" style={{ marginTop: 16 }}>
                            <Button type="default" onClick={loadMoreCatalog} loading={catalogLoadingMore} block>
                                Показати ще
                            </Button>
                        </Flex>
                    )}
                </>
            )}
        </Space.Compact>
    );
}