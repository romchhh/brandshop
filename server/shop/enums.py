from enum import Enum


class OrderStatusEnum(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderPaymentStatusEnum(Enum):
    PENDING = "pending"
    PAYED = "payed"
    CANCELLED = "cancelled"
    IMPOSED_PAYMENT = "imposed_payment"


class OrderDeliveryStatusEnum(Enum):
    PENDING = "pending"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"


class PaymentMethodEnum(Enum):
    ONLINE = "online"
    IMPOSED_PAYMENT = "imposed_payment"
    CRYPTOCURRENCY = "cryptocurrency"
