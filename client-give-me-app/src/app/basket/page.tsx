"use client";

import './index.css'
import Image from 'next/image'
import {CachedRemoteImage} from "@/components/shared/CachedRemoteImage";
import {Flex, Spin, Col, Row, Divider, Space, List, Button} from "antd";
import {useDispatch, useSelector} from "react-redux";
import {useEffect, useMemo, useState} from "react";
import { reduce } from "ramda";

import {RootState} from "@/store/store";
import {useInitData} from "@telegram-apps/sdk-react";
import {getUserId} from "@/lib/helpers";
import {deleteBasketItemRequest, fetchBasketItemsRequest, updateBasketItemRequest} from "@/store/basketItemSlice";
import {isPresent} from "@/lib/utils";
import {emptyText} from "@/components/shared/EmptyText";
import {CloseOutlined} from "@ant-design/icons";
import {Loader} from "@/components/shared/Loader";
import {useBoolean} from "react-use";
import OrderSteps from "@/components/OrderSteps";
import {Viewport} from "next";

export const viewport: Viewport = {
    width: 'device-width',
    height: 'device-height',
    initialScale: 1,
    maximumScale: 1,
    minimumScale: 1,
    userScalable: false,
}

export default function Basket() {
    const dispatch = useDispatch()
    const basketItems = useSelector((state: RootState) => state.basketItem.basketItems);
    const isLoading = useSelector((state: RootState) => state.basketItem.loading);
    const initData = useInitData(true);
    const isEmpty = useMemo(() => !isPresent(basketItems), [basketItems])
    const amount = useMemo(() => reduce((acc, item) => acc + (item.quantity * parseFloat(item.product.price)), 0, basketItems), [basketItems])
    const promotionalAmount = useMemo(() => reduce((acc, item) => acc + item.quantity * (parseFloat(item.product.price) - (parseFloat(item.product.promotional_price) ? parseFloat(item.product.promotional_price) : parseFloat(item.product.price))), 0, basketItems), [basketItems])
    const totalQuantity = useMemo(() => reduce((acc, item) => acc + item.quantity, 0, basketItems), [basketItems])
    const [isOrderSteps, setIsOrderSteps] = useBoolean(false)
    const total = amount - promotionalAmount

    useEffect(() => {
        if (initData) {
            dispatch(fetchBasketItemsRequest(getUserId(initData)))
        }
    }, [initData]);

    const userId = getUserId(initData)

    const onQuantityClick = (basketItem, offset) => dispatch(updateBasketItemRequest({ userId, basketItem, offset}))
    const onDelete = (basketItem) => dispatch(deleteBasketItemRequest({ userId, basketItem}))
    const onRedirect = (url) => window.location.assign(url)
    // const onPay = () => dispatch(createOrderRequest({ userId, onRedirect }))
    const onPay = () => setIsOrderSteps(true)

    if (isOrderSteps) {
        return <OrderSteps total={total} userId={userId} basketItems={basketItems} totalQuantity={totalQuantity} promotionalAmount={promotionalAmount} amount={amount}></OrderSteps>
    }

    return <>
        <Flex justify="center">
            <h1>Кошик</h1>
        </Flex>
        { isLoading && <Loader /> }
        {isEmpty && !isLoading && <Flex gap="large" vertical className="empty-state" align="center" justify="center">
            <Image unoptimized src='/big-basket.svg' alt="Empty basket" width={162} height={145}/>
            <span className='empty-state-text'>На жаль у Вас ще немає доданих товарів у кошику.</span>
        </Flex>}
        {!isEmpty && !isLoading && <>
            <List
                locale={{ emptyText }}
                dataSource={basketItems}
                renderItem={(item) => (
                    <div className="basket-item">
                        <Flex justify="flex-end">
                            <CloseOutlined onClick={() => onDelete(item)}/>
                        </Flex>
                        <Flex gap="large">
                            <div className="basket-item-image">
                                <CachedRemoteImage
                                    src={item.product_property?.photo || item.product.photo}
                                    alt={item.product.title}
                                    width={160}
                                    height={160}
                                    sizes="80px"
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                />
                            </div>
                            <Flex vertical gap="small">
                                <Flex align="flex-start" style={{ height: '33%'}}><span className="product-title">{item.product.title}</span></Flex>
                                {item.product_property && <Flex align="center" style={{ height: '33%'}}><span className="product-property-title">{item.product_property.title}</span></Flex>}
                                <Flex align="flex-end" style={{ height: item.product_property ? '33%' : '77%'}} gap="middle">
                                    <span className="product-price" style={{marginBottom: '5px'}}>{Math.floor(item.product.price)} грн</span>
                                    <Flex className="quantity-container" align="center">
                                        <Image unoptimized src='/plus.svg' width={9} height={19} alt='Plus' onClick={() => onQuantityClick(item, 1)}/>
                                        <span>{item.quantity}</span>
                                        <Image unoptimized src='/minus.svg' width={9} height={19} alt='Minus' onClick={() => onQuantityClick(item, -1)}/>
                                    </Flex>
                                </Flex>
                            </Flex>
                        </Flex>
                    </div>
                )}
            />
            <Flex gap="small" vertical className="total-container">
                <Flex>
                    <span style={{width: '100%'}}>Загальна кількість товарів:</span>
                    <Flex justify="flex-end">
                        <span>{totalQuantity}</span>
                    </Flex>
                </Flex>
                <Flex>
                    <span style={{width: '100%'}}>Сума замовлення:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                        <span className="value">{amount} грн</span>
                    </Flex>
                </Flex>
                <Flex>
                    <span style={{width: '100%'}}>Знижка:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                        <span className="value">{promotionalAmount} грн</span>
                    </Flex>
                </Flex>
                <Divider style={{borderColor: '#B2B2B2', margin: 0}}></Divider>
                <Flex>
                    <span style={{width: '100%'}}>До сплати:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                        <span className="value">{total} грн</span>
                    </Flex>
                </Flex>
            </Flex>
            <div className="custom-button"><Button onClick={onPay}>Замовити</Button></div>
        </>}
    </>;
}
