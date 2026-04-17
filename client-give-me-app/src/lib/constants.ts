export const DEV = false

// export const API_HOST = process.env.NEXT_PUBLIC_API_HOST ||
export const API_HOST = DEV ? 'http://127.0.0.1:8000' : 'https://brandshop.in.ua'

export const ORDER_STATUS = {
    pending: { key: 'pending', locale: 'Очікує підтвердження'},
    completed: { key: 'completed', locale: 'Виконано'},
    cancelled: { key: 'cancelled', locale: 'Скасовано'},
}

export const ORDER_PAYMENT_STATUS = {
    pending: { key: 'pending', locale: 'Очікує оплати'},
    payed: { key: 'payed', locale: 'Оплачено'},
    cancelled: { key: 'cancelled', locale: 'Скасовано'},
    imposed_payment: { key: 'imposed_payment', locale: 'Накладений платіж'},
}

export const ORDER_DELIVERY_STATUS = {
    pending: { key: 'pending', locale: 'Очікує доставки'},
    delivered: { key: 'delivered', locale: 'Доставлено'},
    cancelled: { key: 'cancelled', locale: 'Скасовано'},
}

export const GREEN_ORDER_STATUSES = [ORDER_STATUS.completed.key, ORDER_DELIVERY_STATUS.delivered.key, ORDER_PAYMENT_STATUS.payed.key, ORDER_PAYMENT_STATUS.imposed_payment]
export const RED_ORDER_STATUSES = [ORDER_STATUS.cancelled.key, ORDER_DELIVERY_STATUS.cancelled.key, ORDER_PAYMENT_STATUS.cancelled.key]

