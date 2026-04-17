"use client";

import { Header } from "antd/lib/layout/layout";
import Image from "next/image";
import { Badge } from "antd";
import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/store/store";
import { useInitData } from "@telegram-apps/sdk-react";
import { getUserId } from "@/lib/helpers";
import { fetchUserRequest } from "@/store/userSlice";
import { TABS_PROPS } from "@/app/layout";
import { useRouter } from "next/navigation";

export const NavBar = ({ pathname, showSidebarMenu, setShowSidebarMenu }) => {
    const dispatch = useDispatch();
    const user = useSelector((state: RootState) => state.user.user);
    const initData = useInitData(true);
    const userId = getUserId(initData);
    useEffect(() => {
        if (userId) {
            dispatch(fetchUserRequest({ userId }));
        }
    }, [pathname, userId]);

    const router = useRouter();

    const goToBasket = () => {
        setShowSidebarMenu(false);
        router.push("/basket");
    };
    const goToHome = () => {
        setShowSidebarMenu(false);
        router.push("/");
    };
    const goToCatalog = () => {
        setShowSidebarMenu(false);
        router.push("/catalogs");
    };
    const goToFavorites = () => {
        setShowSidebarMenu(false);
        router.push("/favorites");
    };
    const goToSidebar = () => setShowSidebarMenu(true);

    return (
        <Header className="nav-bar" style={{ position: "sticky", bottom: "0%" }}>
            <div className="nav-item">
                <Image alt="Icon" src="/home-active.svg" onClick={goToHome} className={!showSidebarMenu && pathname === TABS_PROPS.home.path ? "icon-active" : "icon"} width={28} height={24} />
                <span className="nav-label">Головна</span>
            </div>
            <div className="nav-item">
                <Image alt="Icon" src="/catalog.svg" onClick={goToCatalog} className={!showSidebarMenu && pathname === TABS_PROPS.catalog.path ? "icon-active" : "icon"} width={28} height={24} />
                <span className="nav-label">Каталог</span>
            </div>
            <div className="nav-item">
                <Image alt="Icon" src="/heart-active.svg" onClick={goToFavorites} className={!showSidebarMenu && pathname === TABS_PROPS.favorites.path ? "icon-active" : "icon"} width={24} height={24} />
                <span className="nav-label">Обране</span>
            </div>
            <div className="nav-item">
                <Badge count={user?.order_item_total || 0}>
                    <Image alt="Icon" src="/store-active.svg" onClick={goToBasket} className={!showSidebarMenu && pathname === TABS_PROPS.basket.path ? "icon-active" : "icon"} width={28} height={24} />
                </Badge>
                <span className="nav-label">Кошик</span>
            </div>
        </Header>
    );
};
