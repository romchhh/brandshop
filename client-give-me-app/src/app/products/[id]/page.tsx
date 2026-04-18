"use client";

import {Space, Flex, List, Empty, Button, Row, Col, notification, Modal} from 'antd';
import Image from "next/image";
import {CachedRemoteImage} from "@/components/shared/CachedRemoteImage";
import {BackButton} from "@/components/shared/BackButton";
import {useEffect, useState} from "react";
import {useUnmount} from "react-use";
import {useRouter} from "next/navigation";
import {useInitData} from "@telegram-apps/sdk-react";
import {useDispatch, useSelector} from "react-redux";
import {HeartFilled, HeartOutlined} from "@ant-design/icons";
import Link from "next/link";
import {ProductPreview} from "@/components/shared/ProductPreview";

import './index.css'
import {RootState} from "@/store/store";
import {fetchProductRequest, resetProduct, fetchViewProductsRequest} from "@/store/productSlice";
import {getUserId} from "@/lib/helpers";
import {createBasketItemRequest, updateBasketItemRequest} from "@/store/basketItemSlice";
import {Loader} from "@/components/shared/Loader";
import {toggleFavorite} from "@/store/favoriteSlice";
import classNames from "classnames";
import {resolveMediaSrc} from "@/lib/resolveMediaSrc";

const LOG_PREFIX = "[BrandShop] Сторінка товару";

export default function ProductItem({params: {id}}) {
    const dispatch = useDispatch()
    const router = useRouter()

    const product = useSelector((state: RootState) => state.product?.product);
    const basketItem = useSelector((state: RootState) => state.basketItem.basketItem);
    const [resultProduct, setResultProduct] = useState(null)
    const [photo, setPhoto] = useState(null)
    const [selectedProperty, setSelectedProperty] = useState(null)
    const initData = useInitData(true);
    const userId = getUserId(initData)
    const hasDiscount = product?.promotional_price !== null && product?.promotional_price > 0
    const favorites = useSelector((state: RootState) => state.favorite.items || []);
    const isFavorite = product ? favorites.includes(product?.id) : false;
    const viewProducts = useSelector((state: RootState) => state.product?.viewProducts);
    const [recentlyViewed, setRecentlyViewed] = useState(null);

    const onSelectProperty = (property) => {
        setSelectedProperty(property);
        const next = property?.photo || product?.photo;
        setPhoto(next);
        console.log(`${LOG_PREFIX} обрано розмір`, {
            propertyId: property?.id,
            propertyPhotoRaw: property?.photo ?? null,
            fallbackMainPhoto: product?.photo ?? null,
            chosen: next ?? null,
            resolved: next ? resolveMediaSrc(next) : null,
        });
    }

    useEffect(() => {
        if (initData) {
            dispatch(fetchProductRequest({userId, productId: id}))
            dispatch(fetchViewProductsRequest(userId));
        }
    }, [initData]);

    useEffect(() => {
        if (!product)
            return
        setResultProduct(product)
        if (product?.product_properties?.length > 0) {
            setSelectedProperty(product?.product_properties[0])
        }
        const chosen = product?.product_properties?.[0]?.photo || product?.photo;
        setPhoto(chosen);

        const pub = process.env.NEXT_PUBLIC_API_HOST || "";
        console.log(`${LOG_PREFIX} стан після product у Redux`, {
            routeProductId: id,
            mainPhotoRaw: product.photo ?? null,
            firstPropertyPhotoRaw: product.product_properties?.[0]?.photo ?? null,
            chosenForDisplay: chosen ?? null,
            resolvedChosen: chosen ? resolveMediaSrc(chosen) : null,
            NEXT_PUBLIC_API_HOST: pub || "(порожньо — /media/... не допишеться до домену)",
        });
        if (!chosen) {
            console.warn(`${LOG_PREFIX} немає URL фото: і product.photo, і photo у розмірів порожні`, {
                productId: product.id,
                title: product.title,
            });
        }
    }, [product]);

    useEffect(() => {
        if (viewProducts) {
            // Фільтруємо поточний товар і беремо перші 4
            setRecentlyViewed(viewProducts.filter(p => p.id !== parseInt(id)).slice(0, 4));
        }
    }, [viewProducts, id]);

    const addToBasket = () => {
        setIsModalOpen(true)
        dispatch(createBasketItemRequest({userId, productId: id, productPropertyId: selectedProperty?.id}))
    }

    const [isModalOpen, setIsModalOpen] = useState(false);

    const onContinue = () => {
        setIsModalOpen(false);
    };

    const goToBasket = () => {
        setIsModalOpen(false);
        router.push('/basket')
    };
    const onQuantityClick = (basketItem, offset) => dispatch(updateBasketItemRequest({userId, basketItem, offset}))

    useUnmount(() => {
        dispatch(resetProduct())
        setSelectedProperty(null)
    })

    if (!resultProduct) {
        return <Loader/>
    }

    return <>
        <Space.Compact block direction="vertical">
            <BackButton/>
            <div className="product-item-show">
                {photo && (
                    <CachedRemoteImage
                        src={photo}
                        alt={product?.title ?? 'Товар'}
                        width={1200}
                        height={1200}
                        sizes="100vw"
                        priority
                        className="product-item-show-photo"
                        onError={(e) => {
                            console.error(`${LOG_PREFIX} помилка завантаження зображення (onError)`, {
                                routeProductId: id,
                                rawSrc: photo,
                                resolvedSrc: resolveMediaSrc(photo),
                                NEXT_PUBLIC_API_HOST: process.env.NEXT_PUBLIC_API_HOST || "(порожньо)",
                            });
                        }}
                        onLoad={() => {
                            console.log(`${LOG_PREFIX} зображення успішно завантажено`, {
                                routeProductId: id,
                                resolvedSrc: resolveMediaSrc(photo),
                            });
                        }}
                    />
                )}
                <Flex justify="start" vertical gap="small">
                    <div className="product-show-catalog-title">{product?.catalog_title}</div>
                    <div className="product-show-title">{product?.title}</div>
                </Flex>
            </div>
                {product?.product_properties && product.product_properties.length > 0 && (
                    <>
                        <h2>Розміри:</h2>
                        <Space wrap>
                            {product.product_properties.map((property) => (
                                <div
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => onSelectProperty(property)}
                                    onKeyDown={(e) => e.key === 'Enter' && onSelectProperty(property)}
                                    className={selectedProperty?.id === property.id ? 'property-chip-selected' : 'property-chip'}
                                    key={property.id}
                                >
                                    <span
                                        className={
                                            selectedProperty?.id === property.id
                                                ? 'property-chip-selected-text'
                                                : 'property-chip-text'
                                        }
                                    >
                                        {property.title}
                                    </span>
                                </div>
                            ))}
                        </Space>
                    </>
                )}

        </Space.Compact>
        <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="product-show-price">
                {hasDiscount && <div className="product-show-older-price">{Math.floor(product?.price)} ГРН</div>}
                <div>{hasDiscount ? Math.floor(product?.promotional_price) : Math.floor(product?.price)} ГРН</div>
            </div>
            <Flex gap="small" justify="flex-end" align="center">
                <Button
                    icon={isFavorite ? 
                        <HeartFilled style={{ color: '#FF3B30', fontSize: '24px' }} /> : 
                        <HeartOutlined style={{ color: '#FF3B30', fontSize: '24px' }} />
                    }
                    onClick={() => product?.id && dispatch(toggleFavorite(product?.id))}
                    style={{
                        width: '48px',
                        height: '48px',
                        backgroundColor: 'white',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: 'none',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
                    }}
                />
                <Button
                    type="primary"
                    onClick={addToBasket}
                    style={{
                        backgroundColor: '#BEA35E',
                        height: '48px',
                        width: '180px',
                        borderRadius: '24px'
                    }}
                >
                    ЗАМОВИТИ
                </Button>
            </Flex>
        </div>
        <h2>Опис</h2>
        <div className="product-description">
            <span>
                {product?.description?.trim()
                    ? product.description
                    : 'Опис уточнюйте у менеджера.'}
            </span>
        </div>

        {recentlyViewed && recentlyViewed.length > 0 && (
            <>
                <h2 style={{ marginTop: 40, marginBottom: 20, fontSize: 24 }}>Переглянуті товари</h2>
                <List
                    grid={{ gutter: 16, column: 2 }}
                    dataSource={recentlyViewed}
                    className={classNames("list-product-item")}
                    style={{ marginTop: 20 }}
                    renderItem={(item) => (
                        <ProductPreview {...item} />
                    )}
                />
                <div style={{ 
                    display: 'flex', 
                    flexDirection: 'column', 
                    alignItems: 'center',
                    marginTop: 20,
                    marginBottom: 20
                }}>
                    <Link href="/views" style={{ width: '100%' }}>
                        <Button 
                            type="text" 
                            style={{
                                width: '100%',
                                height: '48px',
                                border: '1px solid #bea35e',
                                borderRadius: '24px',
                                color: '#bea35e',
                                backgroundColor: '#fff'
                            }}
                        >
                            ПОКАЗАТИ ЩЕ
                        </Button>
                    </Link>
                </div>
            </>
        )}

        <Modal title="Додано до кошику" open={isModalOpen} onCancel={onContinue} onOk={goToBasket} cancelText="Продовжити" okText="Перейти до кошика">
            <div className="basket-item">
                <Flex gap="large">
                    <div className="product-modal-image">
                        <CachedRemoteImage
                            src={selectedProperty?.photo || product?.photo}
                            alt={product?.title ?? ''}
                            width={180}
                            height={180}
                            sizes="90px"
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                    </div>
                    <Flex vertical gap="small">
                        <Flex align="flex-start" style={{height: '33%'}}><span
                            className="product-title">{product?.title}</span></Flex>
                        {selectedProperty && <Flex align="center" style={{height: '33%'}}><span
                            className="product-property-title">{selectedProperty.title}</span></Flex>}
                        <Flex align="center" style={{height: selectedProperty ? '33%' : '77%'}} gap="middle">
                            <span className="product-price" style={{marginBottom: '5px'}}>{Math.floor(product?.price)} грн</span>
                            <Flex className="quantity-container" align="center">
                                <Image unoptimized src='/plus.svg' width={9} height={19} alt='Plus'
                                       onClick={() => onQuantityClick(basketItem, 1)}/>
                                <span>{basketItem?.quantity}</span>
                                <Image unoptimized src='/minus.svg' width={9} height={19} alt='Minus'
                                       onClick={() => onQuantityClick(basketItem, -1)}/>
                            </Flex>
                        </Flex>
                    </Flex>
                </Flex>
            </div>
        </Modal>
    </>;

}
