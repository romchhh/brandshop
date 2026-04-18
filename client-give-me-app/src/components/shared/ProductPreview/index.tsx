import {Flex, List, Button} from 'antd';
import {CachedRemoteImage} from "@/components/shared/CachedRemoteImage";
import {RootState} from "@/store/store";
import {HeartOutlined, HeartFilled} from '@ant-design/icons';
import './index.css';
import {FC, useState} from "react";
import {useRouter} from "next/navigation";
import classNames from "classnames";
import {useDispatch, useSelector} from "react-redux";
import {toggleFavorite} from "@/store/favoriteSlice";

export interface ProductProps {
    title: string,
    catalogTitle: string,
    photoUrl: string,
    price: number,
    promotionalPrice: number,
    product_properties: Array<{id: number, title: string}>,
}

export const ProductPreview: FC<ProductProps> = ({className, id, title, catalog_title, photo, price, promotional_price, product_properties}) => {
    const router = useRouter();
    const dispatch = useDispatch();
    const favorites = useSelector((state: RootState) => state.favorite.items);
    const isFavorite = favorites.includes(id);
    
    const hasDiscount = promotional_price !== null && promotional_price > 0;
    
    const goToProductShow = () => router.push(`/products/${id}`);
    
    const handleFavoriteClick = (e) => {
        e.stopPropagation();
        dispatch(toggleFavorite(id));
    };

    return (
        <List.Item className={classNames("product-item-preview", className)} onClick={goToProductShow}>
            <Flex vertical style={{ width: '100%' }}>
                <div>
                    <div style={{ position: 'relative' }}>
                        <Flex justify='center' className="product-preview-image-container">
                            {photo && (
                                <CachedRemoteImage
                                    src={photo}
                                    alt={title}
                                    width={800}
                                    height={800}
                                    sizes="(max-width: 768px) 50vw, 200px"
                                    style={{
                                        width: '100%',
                                        height: '100%',
                                        borderRadius: '16px',
                                        objectFit: 'cover',
                                    }}
                                />
                            )}
                        </Flex>
                        <Button
                            icon={isFavorite ? <HeartFilled /> : <HeartOutlined />}
                            onClick={handleFavoriteClick}
                            className="favorite-button"
                            type="text"
                        />
                    </div>
                    <Flex justify="start" vertical>
                        <div className="product-preview-title">{title}</div>
                        <div className="product-preview-catalog-title">{catalog_title}</div>
                        <div className="sizes-container">
                            {product_properties.map((property) => (
                                <div className="size-circle" key={property.id}>
                                    {property.title}
                                </div>
                            ))}
                        </div>
                    </Flex>
                </div>
                <Flex justify="start" vertical>
                    {hasDiscount && <div className="product-preview-older-price">{Math.floor(price)} ГРН</div>}
                    <div className="product-preview-price">{hasDiscount ? Math.floor(promotional_price) : Math.floor(price)} ГРН</div>
                </Flex>
            </Flex>
        </List.Item>
    );
};
