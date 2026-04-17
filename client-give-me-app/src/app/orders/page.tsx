"use client";

import Image from 'next/image'
import {Flex, List, Spin} from "antd";
import Order from "@/components/shared/Order";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {useEffect, useMemo, useState} from "react";
import {useInitData} from "@telegram-apps/sdk-react";
import {isPresent} from "@/lib/utils";
import {fetchBasketItemsRequest} from "@/store/basketItemSlice";
import {getUserId} from "@/lib/helpers";
import {fetchOrdersRequest, resetOrders} from "@/store/orderSlice";
import {emptyText} from "@/components/shared/EmptyText";
import {Loader} from "@/components/shared/Loader";
import {useUnmount} from "react-use";

const order = {
    id: 1,
    status: 'pending',
    payment_status: 'pending',
    delivery_status: 'pending',
    total_amount: 300,
    promotion_amount: 0,
    promocode_amount: 0,
    order_items: [
        {
            id: 1,
            product: {
                id: 1,
                title: 'Test',
                photo: 'https://image.made-in-china.com/202f0j00bcSqPiKyAToQ/Europe-New-Trend-Transparent-Vape-Pods-Kit-Airflow-Adjustable-Rechargeable-Disposable-Vape-Pod.webp',
            },
            product_property: {
                id: 1,
                title: 'Test',
            },
        },
        {
            id: 2,
            product: {
                id: 1,
                title: 'Test',
                photo: 'https://image.made-in-china.com/202f0j00bcSqPiKyAToQ/Europe-New-Trend-Transparent-Vape-Pods-Kit-Airflow-Adjustable-Rechargeable-Disposable-Vape-Pod.webp',
            },
            product_property: {
                id: 1,
                title: 'Test',
            },
        }
    ]
}

export default function Orders() {
    const dispatch = useDispatch()
    const orders = useSelector((state: RootState) => state.order.orders);
    const isLoading = useSelector((state: RootState) => state.order.loading);
    const initData = useInitData(true);
    const isEmpty = useMemo(() => !isPresent(orders), [orders])

    useEffect(() => {
        if (initData) {
            dispatch(fetchOrdersRequest({ status: ['pending'], userId: getUserId(initData) }))
        }
    }, [initData]);

    useUnmount(() => {
        dispatch(resetOrders())
    })

    return <>
        <Flex justify="center">
            <h1>Статус замовлення</h1>
        </Flex>
        { isLoading && <Loader /> }
        {isEmpty && !isLoading && <Flex gap="large" vertical className="empty-state" align="center" justify="center">
                <Image src='/big-box.svg' alt="Empty orders" width={166} height={166} unoptimized/>
                <span className='empty-state-text'>У Вас ще немає замовлення.</span>
        </Flex>}
        { !isEmpty && !isLoading && <List
            locale={{emptyText}}
            dataSource={orders}
            renderItem={(item) => (
                <Order order={item}/>
            )}
        />}
    </>;
}
