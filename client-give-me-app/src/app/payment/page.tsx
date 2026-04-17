"use client";

import {Flex} from "antd";
import Image from 'next/image'

export default function Payment() {
    return <>
        <Flex justify="center">
            <h1>Оплата</h1>
        </Flex>
        <Flex vertical className="info-block">
            <h2>Є декілька способів оплатити замовлення:</h2>
            <span>1. Повна оплата на карту.</span>
            <span>2. Післяплата Нової Пошти (накладний платіж) - по предоплаті на карту.</span>
            <span>3. Сейф-сервіс Нової Пошти.</span>
            <span>4. Оплата криптовалютою.</span>

            <div className="nested-info-block">
                <span>Якщо у Вас є питання ви можете написати нашому консультанту в Telegram</span>
                <Image unoptimized src="/telegram.svg" width={50} height={51} alt="Telegram logo"/>
            </div>
        </Flex>
    </>;
}
