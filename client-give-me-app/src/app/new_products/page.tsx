"use client";

import {Flex, List} from "antd";
import {Search} from "@/components/shared/Search";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {useEffect, useState} from "react";
import {useMount} from "react-use";
import {fetchCatalogsRequest} from "@/store/catalogSlice";
import _ from 'lodash';
import {emptyText} from "@/components/shared/EmptyText";
import {ProductPreview} from "@/components/shared/ProductPreview";
import classNames from "classnames";

const groupProduct = (products) => _.groupBy(products, 'catalog_title')

const getNewProducts = (catalogs) => {
    const newProducts = [];
    catalogs.forEach(catalog => {
        const topProducts = catalog.products.slice(0, 4).map(product => ({
            ...product,
            catalog_title: catalog.title
        }));
        newProducts.push(...topProducts);
    });
    return newProducts;
}

export default function NewProducts() {
    const dispatch = useDispatch()
    const catalogs = useSelector((state: RootState) => state.catalog.catalogs);
    const [groupedProducts, setGroupedProducts] = useState(null)

    const onSearch = (event) => {
        const value = event.target.value
        const newProducts = getNewProducts(catalogs);
        setGroupedProducts(groupProduct(newProducts.filter((product) =>
            product.title.toLowerCase().includes(value.toLowerCase())
        )))
    }

    const onClearSearch = () => {
        const newProducts = getNewProducts(catalogs);
        setGroupedProducts(groupProduct(newProducts))
    }

    useMount(() => {
        dispatch(fetchCatalogsRequest());
    });

    useEffect(() => {
        const newProducts = getNewProducts(catalogs);
        setGroupedProducts(groupProduct(newProducts))
    }, [catalogs]);

    return <>
        <Flex justify="center">
            <h1>Новинки</h1>
        </Flex>
        <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch}/>
        {
            groupedProducts && Object.entries(groupedProducts).map(([catalogTitle, groupProducts]) => (
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
