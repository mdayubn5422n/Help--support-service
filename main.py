"""
Help & Support Microservice   E-commerce project
Run:  uvicorn support_service:app --reload --port 8005
Docs: http://127.0.0.1:8005/docs   (Use Swagger UI to test all endpoints.)
"""
import os
import json
import uuid
import urllib.request
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Help & Support Service", version="1.0")

# URL of another student’s Order service (can be changed using an environment variable)
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8002")

# ---------------------------------------------------------------- DATA ----
TICKETS: Dict[str, dict] = {}   # ticket_id -> ticket (in-memory DB)


class Stage(str, Enum):
    placed = "placed"
    delivered = "delivered"


class Category(str, Enum):
    late_delivery = "late_delivery"
    missing_item = "missing_item"
    wrong_item = "wrong_item"
    damaged_item = "damaged_item"
    quality_issue = "quality_issue"
    payment_issue = "payment_issue"
    refund_status = "refund_status"
    cancel_order = "cancel_order"
    other = "other"


# Issue options similar to Zepto, based on the order stage
CATEGORIES_BY_STAGE = {
    Stage.placed: [
        {"id": "late_delivery", "label": "Order is late"},
        {"id": "cancel_order", "label": "I want to cancel my order"},
        {"id": "payment_issue", "label": "Payment problem / double charged"},
        {"id": "other", "label": "Something else"},
    ],
    Stage.delivered: [
        {"id": "missing_item", "label": "Item missing"},
        {"id": "wrong_item", "label": "Wrong item received"},
        {"id": "damaged_item", "label": "Item damaged / spilled"},
        {"id": "quality_issue", "label": "Quality issue (stale / expired)"},
        {"id": "refund_status", "label": "Where is my refund?"},
        {"id": "other", "label": "Something else"},
    ],
}

# ------------------------------------------------------------- MODELS -----
class OrderEvent(BaseModel):
    order_id: str
    user_id: str


class TicketCreate(BaseModel):
    user_id: str
    order_id: str
    category: Category
    description: Optional[str] = ""


class ChatMessage(BaseModel):
    message: str


# ------------------------------------------------------ ORDER SERVICE -----
def fetch_order(order_id: str) -> dict:
    """Fetch order details from the Order microservice. If that service is not
    running during testing, return mock data."""
    try:
        with urllib.request.urlopen(f"{ORDER_SERVICE_URL}/orders/{order_id}", timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {"order_id": order_id, "status": "UNKNOWN (order service not reachable)",
                "items": [], "total": None}


# -------------------------------------------------------------- AI BOT ----


INTENTS = [
    ("late_delivery", ["late", "delay", "delayed", "not yet", "when will it arrive", "not arrived", "ETA"],
     "Sorry for the delay! 🙏 Your order is currently in {status} status. We are contacting the delivery rider. "
     "If it is not delivered within 15 minutes, we will escalate the ticket so you can receive Support Cash."),

    ("missing_item", ["missing", "not arrived", "less quantity", "not received", "item missing"],
     "We're sorry to hear that 😔 Which item is missing? Let us know, and we'll verify the issue and "
     "send the refund to your original payment method or wallet within 24 hours."),

    ("wrong_item", ["wrong", "incorrect", "different item", "another item"],
     "We're sorry you received the wrong item! Please upload a photo, and we'll arrange a replacement or a full refund."),

    ("damaged_item", ["damaged", "broken", "torn", "spilled", "leaking", "damaged packaging"],
     "We're sorry about the damaged item! Please share a photo, and we'll process the refund once the issue is verified."),

    ("quality_issue", ["stale", "expired", "rotten", "bad taste", "spoiled", "quality", "smell", "bad condition"],
     "Thank you for reporting the quality issue. Please send a photo along with the batch number or expiry date, "
     "and we'll approve the refund."),

    ("payment_issue", ["payment", "money", "double charged", "charged", "deducted", "money deducted", "UPI"],
     "We're sorry about the payment issue. If money was deducted but the order was not created, "
     "an automatic refund is usually processed within 5–7 working days. Share your transaction ID, and we'll check."),

    ("refund_status", ["refund", "money back", "when will I get my money back"],
     "Refunds usually take 3–5 working days to arrive (wallet refunds are processed instantly). "
     "You can check the status in your ticket details."),

    ("cancel_order", ["cancel", "cancellation", "don't want it", "no longer needed"],
     "Your order can be canceled if the rider has not picked it up yet. Please confirm, and we'll submit the cancellation request."),

    ("human", ["agent", "human", "person", "manager", "talk to", "speak to someone", "call"],
     "__ESCALATE__"),
]

def bot_reply(ticket: dict, text: str) -> dict:
    """Rule-based AI. It can later be replaced with an LLM (Claude/OpenAI/Gemini)
    by updating this function."""
    t = text.lower()
    order = fetch_order(ticket["order_id"])
    # 1) Detect the intent from the message
    for intent, words, reply in INTENTS:
        if any(w in t for w in words):
            if reply == "__ESCALATE__":
                ticket["status"] = "escalated"
                return {"reply": "We are connecting you with a support representative. "
                                 "They will contact you shortly. 📞", "escalated": True}
            return {"reply": reply.format(status=order.get("status", "processing")), "escalated": False}
    # 2) If no intent is found, use the ticket category
    for intent, _, reply in INTENTS:
        if intent == ticket["category"] and reply != "__ESCALATE__":
            return {"reply": reply.format(status=order.get("status", "processing")), "escalated": False}
    return {"reply": "Mujhe pura samajh nahi aaya 🙏 Kya aap thoda detail me bata sakte ho? "
                     "Ya 'agent' likho to human support se connect kar dunga.", "escalated": False}


# ------------------------------------------------------------ ENDPOINTS ---
@app.get("/health")
def health():
    return {"service": "help-support", "status": "ok"}


@app.get("/support/categories")
def get_categories(stage: Stage):
    """Return issue options based on the order stage (placed or delivered)."""
    return CATEGORIES_BY_STAGE[stage]


# ---- Other services (Order / Delivery) will call these endpoints ----
@app.post("/events/order-placed")
def order_placed(event: OrderEvent):
    """Called by the Order service when an order is placed."""
    return {
        "order_id": event.order_id,
        "message": "Order placed! Having a problem? We are here to help. 💬",
        "help_button": True,
        "options": CATEGORIES_BY_STAGE[Stage.placed],
    }


@app.post("/events/order-delivered")
def order_delivered(event: OrderEvent):
    """Called by the Delivery service when an order is delivered."""
    return {
        "order_id": event.order_id,
        "message": "Order delivered! Is something wrong? Please let us know. 🙏",
        "help_button": True,
        "options": CATEGORIES_BY_STAGE[Stage.delivered],
    }


# ---- Support tickets ----
@app.post("/support/tickets", status_code=201)
def create_ticket(data: TicketCreate):
    ticket_id = "TKT-" + uuid.uuid4().hex[:8].upper()
    order = fetch_order(data.order_id)
    ticket = {
        "ticket_id": ticket_id,
        "user_id": data.user_id,
        "order_id": data.order_id,
        "category": data.category.value,
        "description": data.description,
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
        "order_snapshot": order,
        "chat": [],
    }
    greeting = bot_reply(ticket, data.description or data.category.value)
    ticket["chat"].append({"from": "bot", "text": greeting["reply"],
                           "time": datetime.utcnow().isoformat()})
    TICKETS[ticket_id] = ticket
    return ticket


@app.get("/support/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    if ticket_id not in TICKETS:
        raise HTTPException(404, "Ticket not found")
    return TICKETS[ticket_id]


@app.get("/support/users/{user_id}/tickets")
def user_tickets(user_id: str) -> List[dict]:
    return [t for t in TICKETS.values() if t["user_id"] == user_id]


@app.post("/support/tickets/{ticket_id}/chat")
def chat(ticket_id: str, msg: ChatMessage):
    """Submit a user message and receive a reply from the AI bot."""
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if ticket["status"] in ("resolved", "closed"):
        raise HTTPException(400, "Ticket already closed")
    now = datetime.utcnow().isoformat()
    ticket["chat"].append({"from": "user", "text": msg.message, "time": now})
    result = bot_reply(ticket, msg.message)
    ticket["chat"].append({"from": "bot", "text": result["reply"], "time": now})
    return {"reply": result["reply"], "escalated": result["escalated"], "status": ticket["status"]}


@app.post("/support/tickets/{ticket_id}/escalate")
def escalate(ticket_id: str):
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket["status"] = "escalated"
    return {"ticket_id": ticket_id, "status": "escalated"}


@app.patch("/support/tickets/{ticket_id}/resolve")
def resolve(ticket_id: str):
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket["status"] = "resolved"
    return {"ticket_id": ticket_id, "status": "resolved"}
