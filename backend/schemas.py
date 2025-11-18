from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class Address(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    landmark: Optional[str] = None
    is_default: bool = True


class User(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: str
    addresses: List[Address] = []


class UserOut(User):
    id: str = Field(..., alias="_id")


class MenuItem(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    veg: bool = True


class MenuItemOut(MenuItem):
    id: str = Field(..., alias="_id")


class OrderItem(BaseModel):
    menu_item_id: str
    quantity: int = 1


class Order(BaseModel):
    customer_id: Optional[str] = None
    guest_details: Optional[User] = None
    items: List[OrderItem]
    total_amount: float
    payment_status: str = "pending"  # pending | paid | failed
    delivery_status: str = "new"      # new | preparing | out_for_delivery | delivered | cancelled
    notes: Optional[str] = None


class OrderOut(Order):
    id: str = Field(..., alias="_id")


class CreateOrderRequest(BaseModel):
    customer_id: Optional[str] = None
    guest_details: Optional[User] = None
    items: List[OrderItem]
    notes: Optional[str] = None


class UpdateOrderStatus(BaseModel):
    payment_status: Optional[str] = None
    delivery_status: Optional[str] = None


class PaymentCreateRequest(BaseModel):
    order_amount: float
    currency: str = "INR"


class PaymentCreateResponse(BaseModel):
    payment_id: str
    amount: float
    currency: str
    provider: str = "mock"


class PaymentConfirmRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: Optional[str] = None
