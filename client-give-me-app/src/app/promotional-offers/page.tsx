"use client";

import {Avatar, Card, Flex, List, Space, Select} from "antd";
import {Search} from "@/components/shared/Search";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {useEffect, useState} from "react";
import {useMount} from "react-use";
import {emptyText} from "@/components/shared/EmptyText";
import {fetchPromotionalProductsRequest} from "@/store/productSlice";
import _ from 'lodash';
import classNames from "classnames";

import './index.css'
import {ProductPreview} from "@/components/shared/ProductPreview";

const groupProduct = (products) => _.groupBy(products, 'catalog_title')

export default function PromotionalOffers() {
    const dispatch = useDispatch()
    const products = useSelector((state: RootState) => state.product.promotionalProducts);
    const [groupedProducts, setGroupedProducts] = useState(null)
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

    const onSearch = (event) => {
        const value = event.target.value
        filterProducts(value, selectedCategory)
    }

    const onClearSearch = () => {
        filterProducts('', selectedCategory)
    }

    const onCategoryChange = (value: string | null) => {
        setSelectedCategory(value)
        filterProducts('', value)
    }

    const filterProducts = (searchValue: string, category: string | null) => {
        let filteredProducts = products;
        
        if (searchValue) {
            filteredProducts = filteredProducts.filter((product) =>
                product.title.toLowerCase().includes(searchValue.toLowerCase())
            )
        }
        
        if (category) {
            filteredProducts = filteredProducts.filter((product) =>
                product.catalog_title === category
            )
        }
        
        setGroupedProducts(groupProduct(filteredProducts))
    }

    const categories = products 
        ? [{ label: 'Всі категорії', value: null }].concat(
            [...new Set(products.map(product => product.catalog_title))]
                .map(category => ({ label: category, value: category }))
        )
        : [];

    useMount(() => {
        dispatch(fetchPromotionalProductsRequest());
    });

    useEffect(() => {
        setGroupedProducts(groupProduct(products))
    }, [products]);


    return <>
        <Flex justify="center">
            <h1>Акційні пропозиції</h1>
        </Flex>
        <Space direction="vertical" style={{ width: '100%' }}>
            <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch}/>
            <Select
                style={{ width: '200px' }}
                placeholder="Оберіть категорію"
                value={selectedCategory}
                onChange={onCategoryChange}
                options={categories}
                allowClear
            />
        </Space>
        {
            groupedProducts && Object.entries(groupedProducts).map(([catalogTitle, groupProducts]) =>(
                <div key={catalogTitle}>
                    <h2 style={{margin: '24px 0 16px 0'}}>{catalogTitle}</h2>
                    <List
                        locale={{ emptyText }}
                        grid={{gutter: 16, column: 2}}
                        dataSource={groupProducts}
                        className={classNames("list-product-item")}
                        style={{marginBottom: 20}}
                        renderItem={(item) => (
                            <ProductPreview {...item}/>
                        )}
                    />
                </div>
            ))
        }
    </>;
}
