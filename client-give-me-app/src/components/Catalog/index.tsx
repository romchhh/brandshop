"use client";

import {Space, Flex, List, Empty} from 'antd';

import {Search} from "@/components/shared/Search";
import {CachedRemoteImage} from "@/components/shared/CachedRemoteImage";

import './index.css'
import {useEffect, useState} from "react";
import {emptyText} from "@/components/shared/EmptyText";
import {useRouter} from "next/navigation";
import {useDispatch, useSelector} from "react-redux";
import {useMount} from "react-use";
import {RootState} from "@/store/store";
import {fetchCatalogsRequest} from "@/store/catalogSlice";

/*const catalogs = [
    {
        id: 1,
        title: 'Title Title dfdfdfdfdf dfdf 232343',
        url: 'https://image.made-in-china.com/202f0j00bcSqPiKyAToQ/Europe-New-Trend-Transparent-Vape-Pods-Kit-Airflow-Adjustable-Rechargeable-Disposable-Vape-Pod.webp'
    },
    {
        id: 2,
        title: 'Title 1',
        url: 'https://b2861582.smushcdn.com/2861582/wp-content/uploads/2023/02/splash-01-605-v1.png?lossy=2&strip=1&webp=1'
    },
    {
        id: 3,
        title: 'Title 2',
        url: 'https://cdn.shopify.com/s/files/1/2303/2711/files/2_e822dae0-14df-4cb8-b145-ea4dc0966b34.jpg?v=1617059123'
    },
    {
        id: 4,
        title: 'Title Title dfdfdfdfdf dfdf 232343',
        url: 'https://image.made-in-china.com/202f0j00bcSqPiKyAToQ/Europe-New-Trend-Transparent-Vape-Pods-Kit-Airflow-Adjustable-Rechargeable-Disposable-Vape-Pod.webp'
    },
    {
        id: 5,
        title: 'Title 1',
        url: 'https://b2861582.smushcdn.com/2861582/wp-content/uploads/2023/02/splash-01-605-v1.png?lossy=2&strip=1&webp=1'
    },
    {
        id: 6,
        title: 'Title 2',
        url: 'https://cdn.shopify.com/s/files/1/2303/2711/files/2_e822dae0-14df-4cb8-b145-ea4dc0966b34.jpg?v=1617059123'
    }
]*/

export default function Catalog() {
    const router = useRouter()
    const catalogs = useSelector((state: RootState) => state.catalog.catalogs);
    const [ resultCatalogs, setResultCatalogs ] = useState(catalogs)
    const dispatch = useDispatch()
    const user = useSelector((state: RootState) => state.user.user)

    const onSearch = (event) => {
        const value = event.target.value.toLowerCase()
        setResultCatalogs(catalogs.filter((catalog) =>
            catalog.title.toLowerCase().includes(value) || catalog.products.find(product => product.title.toLowerCase().includes(value))
        ))
    }
    const onClearSearch = () => {
        setResultCatalogs(catalogs)
    }

    const goToCatalogItemPage = (id) => router.push(`/catalog/${id}`)

    useMount(() => {
        dispatch(fetchCatalogsRequest());
    });

    useEffect(() => {
        setResultCatalogs(catalogs)
    }, [catalogs]);

    return <Space.Compact block direction="vertical">
        { user?.banner && <Flex justify="center">
            <CachedRemoteImage
                src={user.banner}
                width={360}
                height={200}
                alt="Банер"
                className="banner-image"
                sizes="360px"
                style={{ borderRadius: '12px', width: '100%', maxWidth: 360, height: 'auto' }}
                priority
            />
        </Flex>}
        <List
            locale={{ emptyText }}
            dataSource={resultCatalogs}
            renderItem={(item) => (
                <List.Item 
                    className="category-item" 
                    onClick={() => goToCatalogItemPage(item.id)}
                >
                    <div className="category-content">
                        <div className="category-image-container">
                            {(item.photo || item.products?.[0]?.photo) && (
                                <CachedRemoteImage
                                    src={item.photo || item.products?.[0]?.photo}
                                    alt={item.title}
                                    fill
                                    sizes="(max-width: 480px) 100vw, 360px"
                                    style={{ objectFit: 'cover' }}
                                />
                            )}
                        </div>
                        <div className="category-info">
                            <div className="category-title">{item.title.toUpperCase()}</div>
                            <div className="category-count">{item.products?.length || 0} товарів</div>
                            <div className="category-arrow">›</div>
                        </div>
                    </div>
                </List.Item>
            )}
        />
    </Space.Compact>;
};
