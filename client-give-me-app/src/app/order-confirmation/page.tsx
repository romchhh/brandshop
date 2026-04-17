"use client";

import {Flex, Card} from 'antd';
import {CheckCircleOutlined} from '@ant-design/icons';

function OrderConfirmationPage() {
    return (
        <Flex vertical align="center" style={{minHeight: '70vh', padding: '40px 20px'}}>
            <Card 
                style={{
                    maxWidth: 600,
                    width: '100%',
                    textAlign: 'center',
                    borderRadius: '8px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}
            >
                <CheckCircleOutlined style={{fontSize: '48px', color: '#52c41a', marginBottom: '24px'}} />
                
                <h1 style={{
                    fontSize: '28px',
                    marginBottom: '24px',
                    color: '#262626'
                }}>
                    Підтвердження замовлення
                </h1>
                
                <p style={{
                    fontSize: '18px',
                    color: '#595959',
                    lineHeight: '1.5',
                    margin: '0'
                }}>
                    Очікуйте для підтвердження замовлення з вами звʼяжеться наш менеджер.
                </p>
            </Card>
        </Flex>
    );
}

export default OrderConfirmationPage; 