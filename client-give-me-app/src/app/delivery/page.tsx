"use client";

import {Flex} from "antd";
import Image from 'next/image'

export default function Delivery() {
    return <>
        <Flex justify="center">
            <h1>Доставка</h1>
        </Flex>
        <Flex vertical className="info-block">
            <h2>Доставка товару відбувається компанією &quot;Нова Пошта&quot; трьома способам:</h2>
            <span>1. Відправка на відділення.</span>
            <span>2. Кур&apos;єрська доставка за Вашою адресою.</span>
            <span>3. Поштомат.</span>
            <span>Після оформлення замовлення Ви отримаєте номер ТТН, за яким можна відслідковувати статус замовлення у додатку &quot;Нова Пошта&quot;</span>

            <div className="nested-info-block">
                <span>Якщо у Вас є питання ви можете написати нашому консультанту в Telegram</span>
                <Image unoptimized src="/telegram.svg" width={50} height={51} alt="Telegram logo"/>
            </div>
        </Flex>
    </>;
}
