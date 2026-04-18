"use client";

import Head from 'next/head'
import {Inter} from "next/font/google";
import "./globals.css";
import React, {useEffect, useMemo, useState} from "react";
import {Drawer, GetProp, Layout, Menu} from 'antd';
import {Content} from "antd/lib/layout/layout";
import Image from "next/image";
import type { Viewport } from 'next'

import type {MenuProps} from 'antd';
import {usePathname, useRouter} from "next/navigation";
import {Provider} from "react-redux";
import {store} from "@/store/store";
import {SDKProvider} from "@telegram-apps/sdk-react";
import './mockEnv'
import {NavBar} from "@/components/shared/NavBar";
import { NavBarHead } from "@/components/shared/NavBarHead";
import {HeartOutlined, HeartFilled} from '@ant-design/icons';

export const viewport: Viewport = {
    width: 'device-width',
    height: 'device-height',
    initialScale: 1,
    maximumScale: 1,
    minimumScale: 1,
    userScalable: false,
}

const inter = Inter({subsets: ["latin"]});

type MenuItem = GetProp<MenuProps, 'items'>[number];

export const TABS_PROPS = {
    home: {path: '/'},
    catalog: {path: '/catalogs'},
    basket: {path: '/basket'},
    favorites: {path: '/favorites'},
}

const SIDEBAR_PROPS = {
    home: {path: '/'},
    basket: {path: '/basket'},
    new_products: {path: '/new_products'},
    orders: {path: '/orders'},
    catalog: {path: '/catalogs'},
    ordersHistory: {path: '/orders-history'},
    promotionalOffers: {path: '/promotional-offers'},
    payment: {path: '/payment'},
    delivery: {path: '/delivery'},
    favorites: {path: '/favorites'},
    views: {path: '/views'},
}

const SIDEBAR_PATH_MAPPER = {
    '/': ['1'],
    '/catalogs': ['catalog'],
    '/new_products': ['new_products'],
    '/favorites': ['favorites'],
    '/basket': ['2'],
    '/orders': ['3'],
    '/orders-history': ['4'],
    '/promotional-offers': ['5'],
    '/payment': ['6'],
    '/delivery': ['7'],
    '/views': ['views'],
}

export default function RootLayout({
                                       children,
                                   }: Readonly<{
    children: React.ReactNode;
}>) {
    const pathname = usePathname();
    const [showSidebarMenu, setShowSidebarMenu] = useState(false)
    const [selectedKeys, setSelectedKeys] = useState(SIDEBAR_PATH_MAPPER[pathname])

    const router = useRouter();

    const items: MenuItem[] = useMemo(() => [
        {
            key: '1',
            icon: <Image src={pathname === SIDEBAR_PROPS.home.path ? '/home-second-active.svg' : '/home-second.svg'}
                         width={18} height={19} alt="" unoptimized/>,
            label: 'Головна',
            path: '/',
        },
        {
            key: 'catalog',
            icon: <Image src={pathname === SIDEBAR_PROPS.catalog.path ? '/catalog-active.svg' : '/catalog.svg'}
                         width={18} height={19} alt="" unoptimized/>,
            label: 'Каталог',
            path: '/catalogs',
        },
        {
            key: 'new_products',
            icon: <Image src={pathname === SIDEBAR_PROPS.new_products.path ? '/star-active.svg' : '/star.svg'}
                         width={18} height={19} alt="" unoptimized/>,
            label: 'Новинки',
            path: '/new_products',
        },
        {
            key: 'favorites',
            icon: pathname === SIDEBAR_PROPS.favorites.path ? 
                <HeartFilled style={{ color: '#007AFF', fontSize: '18px' }} /> : 
                <HeartOutlined style={{ color: 'black', fontSize: '18px' }} />,
            label: 'Обране',
            path: '/favorites',
        },
        {
            key: 'views',
            icon: <Image src={pathname === SIDEBAR_PROPS.views.path ? '/eye-active.svg' : '/eye.svg'}
                         width={18} height={19} alt="" unoptimized/>,
            label: 'Переглянуті товари',
            path: '/views',
        },
        {
            key: '2',
            icon: <Image src={pathname === SIDEBAR_PROPS.basket.path ? '/basket-active.svg' : '/basket.svg'} width={18}
                         height={19} alt="" unoptimized/>,
            label: 'Кошик',
            path: '/basket',
        },
        {
            key: '3',
            icon: <Image src={pathname === SIDEBAR_PROPS.orders.path ? '/box-active.svg' : '/box.svg'} width={18}
                         height={19} alt="" unoptimized/>,
            label: 'Статус замовлення',
            path: '/orders',
        },
        {
            key: '4',
            icon: <Image src={pathname === SIDEBAR_PROPS.ordersHistory.path ? '/page-active.svg' : '/page.svg'}
                         width={18} height={19} alt="" unoptimized/>,
            label: 'Історія замовлення',
            path: '/orders-history',
        },
        {
            key: '5',
            icon: <Image src={pathname === SIDEBAR_PROPS.promotionalOffers.path ? '/badge-active.svg' : '/badge.svg'}
                         width={18} height={19} alt="" unoptimized/>,
            label: 'Акційні пропозиції',
            path: '/promotional-offers',
        },
        {
            key: '6',
            icon: <Image src={pathname === SIDEBAR_PROPS.payment.path ? '/coin-active.svg' : '/coin.svg'} width={18}
                         height={19} alt="" unoptimized/>,
            label: 'Оплата',
            path: '/payment',
        },
        {
            key: '7',
            icon: <Image src={pathname === SIDEBAR_PROPS.delivery.path ? '/truck-active.svg' : '/truck.svg'} width={18}
                         height={19} alt="" unoptimized/>,
            label: 'Доставка',
            path: '/delivery',
        },
    ], [pathname])

    const onSidebarItemClick = ({item}) => {
        setShowSidebarMenu(false)
        router.push(item.props.path)
    }

    useEffect(() => {
        setSelectedKeys(SIDEBAR_PATH_MAPPER[pathname])
    }, [pathname])


    return (
        <html lang="en">
        <body className={inter.className}>
        <Provider store={store}>
            <SDKProvider>
                <Layout>
                    <NavBarHead pathname={pathname} setShowSidebarMenu={setShowSidebarMenu}
                                showSidebarMenu={showSidebarMenu}></NavBarHead>
                    <Content className="content">
                        {children}
                        <Drawer
                            placement={'left'}
                            closable={true}
                            open={showSidebarMenu}
                            key={'left'}
                            className="sidebar"
                            maskClosable
                            onClose={() => setShowSidebarMenu(false)}
                        >
                            <Menu
                                selectedKeys={selectedKeys}
                                items={items}
                                onSelect={onSidebarItemClick}
                            />
                        </Drawer>
                    </Content>
                    <NavBar pathname={pathname} setShowSidebarMenu={setShowSidebarMenu}
                            showSidebarMenu={showSidebarMenu}></NavBar>
                </Layout>
            </SDKProvider>
        </Provider>
        </body>
        </html>
    );
}
