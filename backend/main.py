from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import os

from schemas import (
    User, UserOut,
    MenuItem, MenuItemOut,
    Order, OrderOut, OrderItem,
    CreateOrderRequest, UpdateOrderStatus,
    PaymentCreateRequest, PaymentCreateResponse, PaymentConfirmRequest,
)
from database import db, create_document, get_documents  # Provided by the environment

app = FastAPI(title="THE HooK API", version="1.0.0")

# CORS to allow frontend
frontend_url = os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IdModel(BaseModel):
    id: str


# Health & DB test
@app.get("/test")
async def test() -> Dict[str, Any]:
    # Ensure DB connectivity
    collections = await db.list_collection_names()
    return {"status": "ok", "db_collections": collections}


# Users
@app.post("/users", response_model=UserOut)
async def create_user(user: User):
    user_dict = user.dict()
    inserted = await create_document("user", user_dict)
    inserted["_id"] = str(inserted["_id"])  # ensure string id
    return inserted

@app.get("/users", response_model=List[UserOut])
async def list_users(limit: int = 50):
    docs = await get_documents("user", {}, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # cast id
    return docs


# Menu
@app.post("/menu", response_model=MenuItemOut)
async def create_menu_item(item: MenuItem):
    inserted = await create_document("menuitem", item.dict())
    inserted["_id"] = str(inserted["_id"])  # cast id
    return inserted

@app.get("/menu", response_model=List[MenuItemOut])
async def list_menu(category: Optional[str] = None, limit: int = 200):
    filter_q: Dict[str, Any] = {}
    if category:
        filter_q["category"] = category
    docs = await get_documents("menuitem", filter_q, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # cast id
    return docs


# Orders
async def compute_total(items: List[OrderItem]) -> float:
    total = 0.0
    for it in items:
        # fetch each menu item price
        try:
            oid = ObjectId(it.menu_item_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid menu_item_id")
        doc_list = await get_documents("menuitem", {"_id": oid}, 1)
        if not doc_list:
            raise HTTPException(status_code=404, detail="Menu item not found")
        price = float(doc_list[0].get("price", 0))
        total += price * it.quantity
    return round(total, 2)


@app.post("/orders", response_model=OrderOut)
async def create_order(payload: CreateOrderRequest):
    # compute total
    total_amount = await compute_total(payload.items)

    order_data = Order(
        customer_id=payload.customer_id,
        guest_details=payload.guest_details,
        items=payload.items,
        total_amount=total_amount,
    ).dict()

    inserted = await create_document("order", order_data)
    inserted["_id"] = str(inserted["_id"])  # cast id
    return inserted


@app.get("/orders", response_model=List[OrderOut])
async def list_orders(limit: int = 100):
    docs = await get_documents("order", {}, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # cast id
    return docs


@app.patch("/orders/{order_id}", response_model=OrderOut)
async def update_order_status(order_id: str, status: UpdateOrderStatus):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")

    updates: Dict[str, Any] = {k: v for k, v in status.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Manual update via db
    result = await db["order"].find_one_and_update(
        {"_id": oid}, {"$set": updates}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result["_id"] = str(result["_id"])  # cast id
    return result


# Payments (placeholder/mock Razorpay/PayTM)
@app.post("/payments/create", response_model=PaymentCreateResponse)
async def create_payment(pay: PaymentCreateRequest):
    # In real flow, call Razorpay Order API and return order/payment id
    payment_id = f"mock_{os.urandom(6).hex()}"
    return PaymentCreateResponse(payment_id=payment_id, amount=pay.order_amount, currency=pay.currency)


@app.post("/payments/confirm")
async def confirm_payment(body: PaymentConfirmRequest):
    # In real flow, verify signature and mark order paid
    try:
        oid = ObjectId(body.order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")

    updated = await db["order"].find_one_and_update(
        {"_id": oid}, {"$set": {"payment_status": "paid"}}, return_document=True
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    updated["_id"] = str(updated["_id"])  # cast id
    return {"status": "success", "order": updated}


# Admin: simple real-time polling endpoint
@app.get("/admin/orders", response_model=List[OrderOut])
async def admin_orders(limit: int = 50):
    docs = await get_documents("order", {}, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # cast id
    return docs
