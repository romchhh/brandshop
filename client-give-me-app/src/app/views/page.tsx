"use client";

import {Flex, List} from "antd";
import {useEffect, useState} from "react";
import {useDispatch, useSelector} from "react-redux";
import { useInitData } from '@telegram-apps/sdk-react';

import {Search} from "@/components/shared/Search";
import {RootState} from "@/store/store";
import {fetchViewProductsRequest} from "@/store/productSlice";
import {emptyText} from "@/components/shared/EmptyText";
import {ProductPreview} from "@/components/shared/ProductPreview";
import {getUserId} from "@/lib/helpers";

export default function Views() {
    const dispatch = useDispatch()
    const products = useSelector((state: RootState) => state.product.viewProducts);
    const [resultProducts, setResultProducts] = useState(null)
    const initData = useInitData(true);

    const onSearch = (event) => {
        const value = event.target.value
        setResultProducts(products.filter((product) =>
                product.title.toLowerCase().includes(value.toLowerCase())
            ))
    }
    const onClearSearch = () => {
        setResultProducts(products)
    }

    useEffect(() => {
        if (initData) {
            dispatch(fetchViewProductsRequest(getUserId(initData)) )
        }
    }, [initData]);

    useEffect(() => {
        setResultProducts(products)
    }, [products]);

    return <>
        <Flex justify="center">
            <h1>Переглянуті товари</h1>
        </Flex>
        <Search placeholder="Пошук товару" handler={onSearch} onClear={onClearSearch}/>
        { resultProducts && <List
            locale={{ emptyText }}
            grid={{gutter: 16, column: 2}}
            dataSource={resultProducts}
            style={{marginTop: 20}}
            renderItem={(item) => (
                <ProductPreview {...item}/>
            )}
        />}
    </>;
}
