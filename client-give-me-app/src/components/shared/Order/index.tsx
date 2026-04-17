"use client";

import {useBoolean} from "react-use";
import Image from "next/image";
import {CachedRemoteImage} from "@/components/shared/CachedRemoteImage";
import {Divider, Flex, List} from "antd";

import './index.css'
import {emptyText} from "@/components/shared/EmptyText";
import {
    GREEN_ORDER_STATUSES,
    ORDER_DELIVERY_STATUS,
    ORDER_PAYMENT_STATUS,
    ORDER_STATUS,
    RED_ORDER_STATUSES
} from "@/lib/constants";
import classNames from "classnames";

const Order = ({order}) => {
    const {id, order_items, total_amount, promotion_amount, promocode_amount, status, payment_status, delivery_status} = order
    const [isOpen, toggleOpenState] = useBoolean(false)

    return <Flex vertical className="order-container" style={{marginBottom: '26px'}}>
        <Flex onClick={toggleOpenState}>
            <span style={{width: '100%'}}>Замовлення №{id}</span>
            <Flex justify="flex-end" align="center" style={{width: '100%'}}>
                <Image src={isOpen ? '/open-state.svg' : '/close-state.svg'} alt="Icon state" width={13} height={13}/>
            </Flex>
        </Flex>
        {
            isOpen && <>
                <Flex>
                    <span style={{width: '100%'}}>Статус замовлення:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                    <span className={classNames('value', {
                            'green': GREEN_ORDER_STATUSES.includes(status),
                            'red': RED_ORDER_STATUSES.includes(status),
                        })}>{ORDER_STATUS[status].locale}</span>
                    </Flex>
                </Flex>
                <Flex>
                    <span style={{width: '100%'}}>Статус оплати:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                        <span className={classNames('value', {
                            'green': GREEN_ORDER_STATUSES.includes(payment_status),
                            'red': RED_ORDER_STATUSES.includes(payment_status),
                        })}>{ORDER_PAYMENT_STATUS[payment_status].locale}</span>
                    </Flex>
                </Flex>
                {/* <Flex>
                    <span style={{width: '100%'}}>Статус доставки:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                        <span className={classNames('value', {
                            'green': GREEN_ORDER_STATUSES.includes(delivery_status),
                            'red': RED_ORDER_STATUSES.includes(delivery_status),
                        })}>{ORDER_DELIVERY_STATUS[delivery_status].locale}</span>
                    </Flex>
                </Flex> */}
                <Divider style={{borderColor: '#B2B2B2', margin: 0}}></Divider>
                <List
                    locale={{emptyText}}
                    dataSource={order_items}
                    renderItem={({product_property, product}) => (
                        <List.Item>
                            <Flex gap="large">
                                <div style={{
                                    width: '123px',
                                    height: '126px',
                                    borderRadius: '15px',
                                    border: '1px solid #E6E6E6',
                                    overflow: 'hidden',
                                    position: 'relative',
                                }}>
                                    <CachedRemoteImage
                                        src={product_property?.photo || product.photo}
                                        alt={product.title}
                                        fill
                                        sizes="123px"
                                        style={{ objectFit: 'cover' }}
                                    />
                                </div>
                                <Flex vertical gap="small">
                                    <Flex align="flex-start" style={{marginBottom: '5px'}}><span
                                        className="product-title">{product.title}</span></Flex>
                                    {product_property && <Flex align="center"><span
                                        className="product-property-title">{product_property.title}</span></Flex>}
                                </Flex>
                            </Flex>
                        </List.Item>
                    )}
                />
                <Divider style={{borderColor: '#B2B2B2', margin: 0}}></Divider>
                    <Flex>
                        <span style={{width: '100%'}}>Сума замовлення:</span>
                        <Flex justify="flex-end" style={{width: '100%'}}>
                            <span className="value">{total_amount} грн</span>
                        </Flex>
                    </Flex>
                    <Flex>
                        <span style={{width: '100%'}}>Знижка:</span>
                        <Flex justify="flex-end" style={{width: '100%'}}>
                            <span className="value">{promotion_amount} грн</span>
                        </Flex>
                    </Flex>
                    <Flex>
                        <span style={{width: '100%'}}>Знижка за промокодом:</span>
                        <Flex justify="flex-end" style={{width: '100%'}}>
                            <span className="value">{promocode_amount} грн</span>
                        </Flex>
                    </Flex>
                <Divider style={{borderColor: '#B2B2B2', margin: 0}}></Divider>
                <Flex>
                    <span style={{width: '100%'}}>Загальна вартість:</span>
                    <Flex justify="flex-end" style={{width: '100%'}}>
                        <span className="value">{total_amount - promotion_amount- promocode_amount} грн</span>
                    </Flex>
                </Flex>
            </>
        }
    </Flex>
}

export default Order
