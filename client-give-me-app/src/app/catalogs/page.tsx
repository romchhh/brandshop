"use client";

import {Space, Row, Col, Flex} from 'antd';
import Catalog from "@/components/Catalog";
import {BackButton} from "@/components/shared/BackButton";

export default function CatalogsPage() {
    return (
        <Space.Compact block direction="vertical">
            <Row>
                <Col span={2}>
                    <Flex align="center" style={{ height: '100%' }}>
                        <BackButton />
                    </Flex>
                </Col>
                <Col span={20}>
                    <Flex justify="center" style={{ width: '100%' }}>
                        <h1>Каталог</h1>
                    </Flex>
                </Col>
            </Row>
            <Catalog />
        </Space.Compact>
    );
} 