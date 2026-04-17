"use client";

import {Button, Divider, Flex, Input, InputNumber, List, Steps, Select, Spin, Form} from "antd";
import {emptyText} from "@/components/shared/EmptyText";
import Image from "next/image";
import {useMemo, useState} from "react";
import {useBoolean, useUnmount} from "react-use";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {fetchCitiesRequest, fetchWarehousesRequest, resetWarehouses} from "@/store/novaPoshtaSlice";
import {isPresent} from "@/lib/utils";
import {createOrderRequest} from "@/store/orderSlice";
import {fetchPromocodeRequest, resetPromocode} from "@/store/promocodeSlice";

const steps = [
    {
        title: 'Замовлення',
    },
    {
        title: 'Доставка і оплата',
    },
];

const NAME_REGEX = /^[А-ЯІЇЄҐа-яіїєґ]+(?:-[А-ЯІЇЄҐа-яіїєґ]+)?\s+[А-ЯІЇЄҐа-яіїєґ]+(?:-[А-ЯІЇЄҐа-яіїєґ]+)?\s*$/;
const PAYMENTS = {
    online: 'online',
    imposed: 'imposed_payment',
    cryptocurrency: 'cryptocurrency',
}
const PAYMENT_OPTIONS = [
    {
        label: 'Оплата на карту',
        value: PAYMENTS.online
    },
    {
        label: 'Накладений платіж',
        value: PAYMENTS.imposed
    },
]

const DELIVERY_METHODS = {
    novaPoshta: 'Нова пошта',
    pickupPravdy: 'Самовивіз з магазину Правди 7',
    pickupSkovorody: 'Самовивіз з магазину Григорія Сковороди 51'
}

const DELIVERY_OPTIONS = [
    {
        label: 'Нова пошта',
        value: DELIVERY_METHODS.novaPoshta
    },
    {
        label: 'Самовивіз з магазину Правди 7',
        value: DELIVERY_METHODS.pickupPravdy
    },
    {
        label: 'Самовивіз з магазину Григорія Сковороди 51',
        value: DELIVERY_METHODS.pickupSkovorody
    }
]

export default function OrderSteps({basketItems, totalQuantity, amount, promotionalAmount, userId, total}) {
    const [current, setCurrent] = useState(0);
    const items = steps.map((item) => ({key: item.title, title: item.title}));
    const [isOpenPromocode, setIsOpenPromocode] = useBoolean(false)
    const goNextStep = () => setCurrent(current + 1)
    const dispatch = useDispatch()
    const cities = useSelector((state: RootState) => state.novaPoshta.cities);
    const warehouses = useSelector((state: RootState) => state.novaPoshta.warehouses);
    const isCitiesLoading = useSelector((state: RootState) => state.novaPoshta.citiesLoading);
    const isWarehousesLoading = useSelector((state: RootState) => state.novaPoshta.warehousesLoading);
    const promocode = useSelector((state: RootState) => state.promocode.promocode);
    const citiesOptions = cities.map((city) => ({label: city.Present, value: city.DeliveryCity}))
    const warehousesOptions = warehouses.map((warehouse) => ({label: warehouse.Description, value: warehouse.Ref}))
    const onCitiesSearch = (value) => {
        dispatch(fetchCitiesRequest({cityName: value}))
    }

    const [form] = Form.useForm();
    const cityValue = Form.useWatch('city', form);
    const onWarehousesSearch = (value) => {
        dispatch(fetchWarehousesRequest({cityRef: cityValue.value, search: value}))
    }
    const onCityChange = () => {
        dispatch(resetWarehouses())
        form.setFieldsValue({warehouse: null});
    }
    const paymentValue = Form.useWatch('paymentMethod', form);
    const deliveryMethod = Form.useWatch('deliveryMethod', form);
    const showNovaPoshtaFields = deliveryMethod === DELIVERY_METHODS.novaPoshta;
    const onRedirect = (url) => {
        if (url) {
            window.location.assign(url)
        } else {
            window.location.assign('/order-confirmation')
        }
    }
    const promocodePromotional = useMemo(() => {
            if (isPresent(promocode?.discount)) {
                return total * (parseFloat(promocode.discount) / 100)
            }

            return 0
        }
        , [total, promocode]
    )

    const onSubmitForm = (values) => {
        const formData = {
            userId,
            onRedirect,
            ...values,
            ...(values.city && { city: values.city.label }),
            ...(values.warehouse && { warehouse: values.warehouse.label }),
            promocodeId: promocode?.id,
        }
        
        dispatch(createOrderRequest(formData))
    }

    const [promocodeValue, setPromocodeValue] = useState('');
    const onApplyPromocode = () => {
        dispatch(fetchPromocodeRequest({userId, promocode: promocodeValue}))
    }
    const onChangePromocode = (event) => setPromocodeValue(event.target.value)

    useUnmount(() => dispatch(resetPromocode()))

    return (
        <>
            <Steps style={{marginBottom: '26px'}} responsive={false} direction="horizontal" labelPlacement="horizontal"
                   current={current} items={items}/>
            {current === 0 && <>
                <div className="basket-item">
                    <List
                        locale={{emptyText}}
                        dataSource={basketItems}
                        renderItem={({product_property, product}) => (
                            <List.Item>
                                <Flex gap="large">
                                    <Image
                                        src={product_property?.photo || product.photo}
                                        width={123}
                                        height={126}
                                        sizes="123px"
                                        style={{ borderRadius: '15px', border: '1px solid #E6E6E6', objectFit: 'cover' }}
                                        alt={product.title}
                                    />
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
                </div>
                <Flex gap="small" vertical className="total-container">
                    {!isOpenPromocode && <Flex>
                        <span onClick={() => setIsOpenPromocode(true)} style={{'text-decoration': 'underline'}}>
                            Застосувати промокод
                        </span>
                    </Flex>}
                    {
                        isOpenPromocode && <Flex gap="small">
                            <Input placeholder="Промокод" onChange={onChangePromocode}/>
                            <Button onClick={onApplyPromocode}>Застосувати</Button>
                        </Flex>
                    }
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
                    <Flex>
                        <span style={{width: '100%'}}>Знижка за промокодом:</span>
                        <Flex justify="flex-end" style={{width: '100%'}}>
                            <span className="value">{promocodePromotional} грн</span>
                        </Flex>
                    </Flex>
                    <Divider style={{borderColor: '#B2B2B2', margin: 0}}></Divider>
                    <Flex>
                        <span style={{width: '100%'}}>До сплати:</span>
                        <Flex justify="flex-end" style={{width: '100%'}}>
                            <span className="value">{total - promocodePromotional} грн</span>
                        </Flex>
                    </Flex>
                </Flex>
                <div className="custom-button" style={{marginTop: '10px'}}><Button onClick={goNextStep}>Далі</Button>
                </div>
            </>}
            {
                current === 1 && <>
                    <Flex gap="small" vertical wrap>
                        <Form name="default" form={form} onFinish={onSubmitForm}
                              initialValues={{
                                  paymentMethod: PAYMENTS.online,
                                  deliveryMethod: DELIVERY_METHODS.novaPoshta
                              }}>
                            <Form.Item name="fullName" rules={[{
                                required: true,
                                message: 'Поле обов`язкове'
                            }, {message: 'Неправильний формат', pattern: NAME_REGEX}]}>
                                <Input size="large" placeholder="Прізвище і імʼя" style={{width: '100%'}}/>
                            </Form.Item>
                            <Form.Item name="phoneNumber" rules={[{
                                required: true,
                                message: 'Поле обов`язкове'
                            }, {message: 'Введіть повний номер телефону', pattern: /\d{9}/i}]}>
                                <InputNumber size="large" prefix="+380" style={{width: '100%'}}/>
                            </Form.Item>
                            <Form.Item name="deliveryMethod" rules={[{required: true, message: 'Поле обов`язкове'}]}
                                      label="Спосіб доставки">
                                <Select
                                    size="large"
                                    options={DELIVERY_OPTIONS}
                                    defaultValue={DELIVERY_METHODS.novaPoshta}
                                />
                            </Form.Item>

                            {showNovaPoshtaFields && (
                                <>
                                    <Form.Item name="city" 
                                        rules={showNovaPoshtaFields ? [{required: true, message: 'Поле обов`язкове'}] : []}>
                                        <Select
                                            style={{width: '100%'}}
                                            size="large"
                                            labelInValue
                                            allowClear
                                            showSearch
                                            filterOption={false}
                                            onSearch={onCitiesSearch}
                                            notFoundContent={isCitiesLoading ? <Spin size="small"/> : null}
                                            options={citiesOptions}
                                            onChange={onCityChange}
                                            placeholder="Місто доставки"
                                        />
                                    </Form.Item>
                                    {isPresent(cityValue) &&
                                        <Form.Item name="warehouse" 
                                            rules={showNovaPoshtaFields ? [{required: true, message: 'Поле обов`язкове'}] : []}>
                                            <Select
                                                style={{width: '100%'}}
                                                size="large"
                                                labelInValue
                                                allowClear
                                                showSearch
                                                filterOption={false}
                                                onClick={() => onWarehousesSearch("")}
                                                onSearch={onWarehousesSearch}
                                                notFoundContent={isWarehousesLoading ? <Spin size="small"/> :  null}
                                                options={warehousesOptions}
                                                placeholder="Відділення"
                                                onSelect={() => {
                                                    (document.activeElement as HTMLElement)?.blur();
                                                }}
                                            />
                                        </Form.Item>
                                    }
                                </>
                            )}
                            <Form.Item name="paymentMethod" rules={[{required: true, message: 'Поле обов`язкове'}]}
                                       style={{marginTop: '10px'}} label="Спосіб оплати">
                                <Select
                                    size="large"
                                    options={PAYMENT_OPTIONS}
                                    defaultValue={PAYMENTS.online}
                                />
                            </Form.Item>
                            <Form.Item name="notes" label="Коментар до замовлення">
                                <Input.TextArea 
                                    size="large"
                                    placeholder="При замовленні одягу вкажіть ваш зріст та вагу&#10;. При замовленні взуття вкажіть розмір в см"
                                    rows={4}
                                />
                            </Form.Item>
                            <div className="custom-button" style={{marginTop: '10px'}}>
                                <Button htmlType="submit">Підтвердити</Button>
                            </div>
                        </Form>
                    </Flex>
                </>
            }
        </>
    )
}
