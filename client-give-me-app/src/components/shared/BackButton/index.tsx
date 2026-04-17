import {FC} from "react";
import {ProductProps} from "@/components/shared/ProductPreview";
import {useRouter} from "next/navigation";
import {ArrowLeftOutlined} from "@ant-design/icons";

import './index.css'
import {Flex} from "antd";

export const BackButton: FC = () => {
    const router = useRouter()
    const goBack = () => router.back()

    return <Flex justify="center" align="center" className="back-button-container" onClick={goBack}>
            <ArrowLeftOutlined />
        </Flex>
}
