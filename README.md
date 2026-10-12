# Help & Support Service

FastAPI based Help & Support Service.

## Run Locally
pip install -r requirements.txt
uvicorn Help:app --reload --port 8005
Then open: http://127.0.0.1:8005/docs

## API Categories
- late_delivery, missing_item, wrong_item, damaged_item, quality_issue, payment_issue, refund_status, cancel_order, other
