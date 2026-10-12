# Delivery Service (Microservice) - Port 8004

## Setup (virtual environment)

Windows:
    python -m venv venv
    venv\Scripts\activate
Mac/Linux:
    python3 -m venv venv
    source venv/bin/activate

    pip install -r requirements.txt
    uvicorn main:app --reload --port 8004

Swagger docs (test yahin se karo): http://127.0.0.1:8004/docs

## Endpoints

| Method | URL | Kaam |
|---|---|---|
| GET  | /                                   | health check |
| GET  | /serviceability/{pincode}           | pincode par delivery hai ya nahi + date |
| GET  | /delivery-estimate?pincode=&order_value=&payment_mode= | delivery date + charge |
| POST | /shipments                          | shipment banao (Order service call karegi) |
| GET  | /shipments                          | sab shipments (?status=SHIPPED) |
| GET  | /shipments/order/{order_id}         | order_id se shipment |
| GET  | /track/{tracking_id}                | tracking timeline |
| PUT  | /shipments/{tracking_id}/status     | PACKED / SHIPPED / OUT_FOR_DELIVERY |
| POST | /agents  , GET /agents              | delivery agent add / list |
| POST | /shipments/{tracking_id}/assign-agent | agent assign |
| POST | /shipments/{tracking_id}/verify-otp | OTP se DELIVERED |
| POST | /shipments/{tracking_id}/cancel     | cancel |
| POST | /shipments/{tracking_id}/return     | return (7 din ke andar) |

## Test flow (Swagger me is order me chalao)
1. POST /agents          {"name":"Ramesh","phone":"9876543210","area_pincode":"560001"}
2. POST /shipments       {"order_id":"ORD1001","customer_name":"Asha","phone":"9876501234",
                          "address":"MG Road, Bengaluru","pincode":"560001","order_value":799,
                          "payment_mode":"PREPAID","items":["Shoes"]}
3. PUT  /shipments/{tracking_id}/status   {"status":"PACKED"}
4. PUT  ... {"status":"SHIPPED"}
5. POST /shipments/{tracking_id}/assign-agent   {"agent_id":1}
6. PUT  ... {"status":"OUT_FOR_DELIVERY"}   -> response me demo OTP aayega
7. POST /shipments/{tracking_id}/verify-otp  {"otp":"1234"}  -> DELIVERED
8. GET  /track/{tracking_id}   -> poori timeline

## Dusre services se link kaise hoga (integration)
Sab services alag ports par chalengi, aur HTTP se baat karengi, e.g.:
    Order service   -> localhost:8002
    Delivery (tum)  -> localhost:8004

Order service me order place hone ke baad:

    import requests
    r = requests.post("http://127.0.0.1:8004/shipments", json={
        "order_id": order_id, "customer_name": name, "phone": phone,
        "address": address, "pincode": pincode,
        "order_value": total, "payment_mode": "PREPAID", "items": ["Shoes"]})
    tracking_id = r.json()["tracking_id"]

Product/Cart service checkout par:
    requests.get("http://127.0.0.1:8004/delivery-estimate",
                 params={"pincode": "560001", "order_value": 799})

Sab students ko ek hi rule follow karna hai: apna port + endpoints ki list share karo,
aur data JSON me bhejo. Final project me bas ek `run_all` script / docker-compose se
saari services ek saath start ho jayengi.
