"use client";

import Image from 'next/image'
import {Flex, List} from "antd";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {useInitData} from "@telegram-apps/sdk-react";
import {useEffect, useMemo} from "react";
import {isPresent} from "@/lib/utils";
import {fetchOrdersRequest, resetOrders} from "@/store/orderSlice";
import {getUserId} from "@/lib/helpers";
import {useUnmount} from "react-use";
import {Loader} from "@/components/shared/Loader";
import {emptyText} from "@/components/shared/EmptyText";
import Order from "@/components/shared/Order";

export default function OrdersHistory() {
    const dispatch = useDispatch()
    const orders = useSelector((state: RootState) => state.order.orders);
    const isLoading = useSelector((state: RootState) => state.order.loading);
    const initData = useInitData(true);
    const isEmpty = useMemo(() => !isPresent(orders), [orders])

    useEffect(() => {
        if (initData) {
            dispatch(fetchOrdersRequest({ status: ['cancelled', 'completed'], userId: getUserId(initData) }))
        }
    }, [initData]);

    useUnmount(() => {
        dispatch(resetOrders())
    })

    return <>
        <Flex justify="center">
            <h1>Історія замовлень</h1>
        </Flex>
        { isLoading && <Loader /> }
        {isEmpty && !isLoading &&<Flex  gap="large" vertical className="empty-state" align="center" justify="center">
                <Image unoptimized src='/big-page.svg' alt="Empty orders" width={166} height={166}/>
                <span className='empty-state-text'>У Вас ще немає замовлень.</span>
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
