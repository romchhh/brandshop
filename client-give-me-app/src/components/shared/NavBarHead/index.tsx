"use client";

import {Header} from "antd/lib/layout/layout";
import Image from "next/image";
import {Badge} from "antd";
import React, {useEffect} from "react";
import {useDispatch, useSelector} from "react-redux";
import {RootState} from "@/store/store";
import {useInitData} from "@telegram-apps/sdk-react";
import {getUserId} from "@/lib/helpers";
import {fetchUserRequest} from "@/store/userSlice";
import {TABS_PROPS} from "@/app/layout";
import {useRouter} from "next/navigation";

export const NavBarHead = ({pathname, showSidebarMenu, setShowSidebarMenu}) => {
    const dispatch = useDispatch()
    const user = useSelector((state: RootState) => state.user.user);
    const initData = useInitData(true);
    const userId = getUserId(initData)
    useEffect(() => {
        if (userId) {
            dispatch(fetchUserRequest({userId}))
        }
    }, [pathname, userId])

    const router = useRouter();

    const goToBasket = () => {
        setShowSidebarMenu(false)
        router.push('/basket')
    }
    const goToCatalog = () => {
        setShowSidebarMenu(false)
        router.push('/')
    }
    const goToViews = () => {
        setShowSidebarMenu(false)
        router.push('/views')
    }
    const goToSidebar = () => setShowSidebarMenu(true)

    const goToTelegram = () => {
        window.open('https://t.me/brandshop777', '_blank');
    }

    return <Header className="nav-bar-head">
        <Image
            alt=""
            className="icon-active"
            src={showSidebarMenu ? "/description-active.svg" : "/description.svg"}
            onClick={goToSidebar}
            width={28}
            height={24}
            unoptimized
            style={{ cursor: "pointer", flexShrink: 0 }}
        />
        <a
            href="/"
            className="brand-logo"
            style={{
                fontSize: "24px",
                fontWeight: "bold",
                color: "#111111",
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
        >
            BRANDSHOP777
        </a>
        <div style={{ display: "flex", gap: "12px", alignItems: "center", flexShrink: 0 }}>
            <Image 
                alt="Telegram"
                src="/telegram.svg"
                unoptimized
                width={28}
                height={24}
                onClick={goToTelegram}
            />
            <Badge count={user?.order_item_total || 0}>
                <Image alt="Icon"
                       className="icon-active"
                       src={!showSidebarMenu && pathname === TABS_PROPS.basket.path ? '/store-active.svg' : '/store.svg'}
                       unoptimized
                       width={28} height={24} onClick={goToBasket}/>
            </Badge>
        </div>
    </Header>
}
