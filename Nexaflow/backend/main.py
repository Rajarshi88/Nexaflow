from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta
from typing import Optional
import asyncio
import random
import pandas as pd
import io
import hashlib
import hmac
import json
import os
import secrets
import urllib.error
import urllib.request

from dotenv import load_dotenv

from models import (
    init_db, get_db, Product, Customer, Order, OrderItem, Campaign, Message,
    PipelineRun, InventoryLog, Settings, SignupOtp
)
from forecast import calculate_forecast, calculate_all_forecasts, calculate_alerts, calculate_stock_health, get_settings
from matching import match_customers_for_product, generate_message
from agent import AgentOrchestrator, trigger_restock_cascade

load_dotenv()

app = FastAPI(title="NexaFlow API")
init_db()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "https://8hm04pj7-5173.inc1.devtunnels.ms",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Backend OTP + Brevo API authentication ============
class SignupOtpRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

class VerifySignupOtpRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    otp: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=8, max_length=128)

def _clean_email(email: str) -> str:
    return email.strip().lower()

def _otp_hash(otp: str) -> str:
    secret = os.getenv('OTP_HASH_SECRET', 'nexaflow-local-otp-secret').encode('utf-8')
    return hmac.new(secret, otp.encode('utf-8'), hashlib.sha256).hexdigest()

def _send_brevo_otp(email: str, business_name: str, otp: str) -> None:
    api_key = os.getenv('BREVO_API_KEY', '').strip()
    sender_email = os.getenv('BREVO_SENDER_EMAIL', '').strip()
    sender_name = os.getenv('BREVO_SENDER_NAME', 'NexaFlow').strip()
    if not api_key or not sender_email:
        raise HTTPException(status_code=503, detail='Backend email is not configured. Add BREVO_API_KEY and BREVO_SENDER_EMAIL to backend/.env.')
    payload = {
        'sender': {'name': sender_name, 'email': sender_email},
        'to': [{'email': email}],
        'subject': 'Your NexaFlow verification code',
        'htmlContent': f'''<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:24px;color:#17322f"><h2>Verify your NexaFlow account</h2><p>Hi {business_name},</p><p>Use this one-time code to finish creating your business account:</p><div style="font-size:32px;font-weight:700;letter-spacing:10px;padding:18px 0;color:#126555">{otp}</div><p>This code expires in 10 minutes. If you did not request this, you can ignore this email.</p></div>'''
    }
    request = urllib.request.Request(
        'https://api.brevo.com/v3/smtp/email',
        data=json.dumps(payload).encode('utf-8'),
        headers={'accept': 'application/json', 'api-key': api_key, 'content-type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise HTTPException(status_code=502, detail='Brevo rejected the email request.')
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace')
        raise HTTPException(status_code=502, detail=f'Brevo email error: {detail[:300]}')
    except urllib.error.URLError:
        raise HTTPException(status_code=502, detail='Could not reach Brevo over HTTPS.')

def _create_supabase_user(email: str, password: str, business_name: str) -> dict:
    supabase_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not supabase_url or not service_key:
        raise HTTPException(status_code=503, detail='Backend Supabase admin access is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to backend/.env.')
    request = urllib.request.Request(
        f'{supabase_url}/auth/v1/admin/users',
        data=json.dumps({'email': email, 'password': password, 'email_confirm': True, 'user_metadata': {'business_name': business_name}}).encode('utf-8'),
        headers={'accept': 'application/json', 'apikey': service_key, 'authorization': f'Bearer {service_key}', 'content-type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace')
        if error.code in (400, 422) and ('already' in detail.lower() or 'registered' in detail.lower()):
            raise HTTPException(status_code=409, detail='An account with this email already exists. Please sign in instead.')
        raise HTTPException(status_code=502, detail=f'Supabase user creation failed: {detail[:300]}')
    except urllib.error.URLError:
        raise HTTPException(status_code=502, detail='Could not reach Supabase from the backend.')

@app.post('/api/auth/request-signup-otp')
async def request_signup_otp(payload: SignupOtpRequest, db: Session = Depends(get_db)):
    email = _clean_email(payload.email)
    now = datetime.utcnow()
    cooldown = int(os.getenv('OTP_RESEND_SECONDS', '60'))
    recent = db.query(SignupOtp).filter(SignupOtp.email == email, SignupOtp.created_at >= now - timedelta(seconds=cooldown), SignupOtp.used_at.is_(None)).first()
    if recent:
        raise HTTPException(status_code=429, detail=f'Please wait {cooldown} seconds before requesting another code.')
    otp = f'{secrets.randbelow(1000000):06d}'
    record = SignupOtp(email=email, business_name=payload.business_name.strip(), otp_hash=_otp_hash(otp), expires_at=now + timedelta(minutes=int(os.getenv('OTP_EXPIRY_MINUTES', '10'))))
    db.query(SignupOtp).filter(SignupOtp.email == email, SignupOtp.used_at.is_(None)).delete(synchronize_session=False)
    db.add(record)
    db.commit()
    try:
        _send_brevo_otp(email, record.business_name, otp)
    except HTTPException:
        db.delete(record)
        db.commit()
        raise
    return {'success': True, 'message': 'Verification code sent.'}

@app.post('/api/auth/verify-signup-otp')
async def verify_signup_otp(payload: VerifySignupOtpRequest, db: Session = Depends(get_db)):
    email = _clean_email(payload.email)
    record = db.query(SignupOtp).filter(SignupOtp.email == email, SignupOtp.used_at.is_(None)).order_by(desc(SignupOtp.created_at)).first()
    if not record:
        raise HTTPException(status_code=400, detail='No active verification code found. Request a new code.')
    if record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail='This verification code has expired. Request a new code.')
    if record.attempts >= 5:
        raise HTTPException(status_code=429, detail='Too many incorrect attempts. Request a new code.')
    if not hmac.compare_digest(record.otp_hash, _otp_hash(payload.otp.strip())):
        record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail='Incorrect verification code.')
    user = _create_supabase_user(email, payload.password, record.business_name)
    record.used_at = datetime.utcnow()
    db.commit()
    return {'success': True, 'user_id': user.get('id'), 'message': 'Account created. You can now sign in.'}

# ============ Overview Endpoints ============

@app.get("/api/overview")
async def get_overview(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get overview dashboard data"""

    # Parse date range or default to last 16 days
    if not end_date:
        end_dt = datetime.now()
    else:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    if not start_date:
        start_dt = end_dt - timedelta(days=15)
    else:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')

    # Previous period for comparison
    period_length = (end_dt - start_dt).days
    prev_start = start_dt - timedelta(days=period_length)
    prev_end = start_dt

    # KPI 1: Forecasted revenue
    forecasts = calculate_all_forecasts(db)
    total_forecast = sum([
        sum([f['demand'] for f in fc['forecast']]) *
        db.query(Product).filter(Product.sku == fc['sku']).first().price
        for fc in forecasts
    ])

    prev_revenue = db.query(func.sum(Order.total_amount)).filter(
        and_(Order.order_date >= prev_start, Order.order_date < prev_end)
    ).scalar() or 0

    current_revenue = db.query(func.sum(Order.total_amount)).filter(
        and_(Order.order_date >= start_dt, Order.order_date <= end_dt)
    ).scalar() or 0

    revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 12.4

    # KPI 2: Items needing attention
    alerts = calculate_alerts(db)
    needs_attention = len([a for a in alerts if a['status'] in ['critical', 'reorder_soon', 'out_of_stock']])
    critical_count = len([a for a in alerts if a['status'] == 'critical'])

    # KPI 3: Re-engagement rate
    total_messages = db.query(Message).filter(Message.status.in_(['sent', 'delivered', 'read', 'clicked'])).count()
    clicked = db.query(Message).filter(Message.status == 'clicked').count()
    reengagement_rate = (clicked / total_messages * 100) if total_messages > 0 else 24.8

    # KPI 4: Campaign revenue
    campaign_revenue = db.query(func.sum(Campaign.revenue)).scalar() or 0
    # Simulate increase
    campaign_revenue_change = 18.7

    # Demand forecast chart (next 7 days)
    daily_forecasts = []
    for i in range(7):
        date = datetime.now() + timedelta(days=i)
        day_total = sum([
            fc['forecast'][i]['demand'] if i < len(fc['forecast']) else 0
            for fc in forecasts
        ])
        daily_forecasts.append({
            'day': date.strftime('%a'),
            'forecasted': round(day_total, 1),
            'historical': round(day_total * 0.85, 1)  # Simulate historical
        })

    # Stock health
    stock_health = calculate_stock_health(db)

    # Last pipeline run
    last_run = db.query(PipelineRun).order_by(desc(PipelineRun.started_at)).first()

    if last_run:
        minutes_ago = int((datetime.now() - last_run.started_at).seconds / 60)
        last_run_text = f"{minutes_ago} minutes ago" if minutes_ago > 0 else "just now"
        customers_matched = last_run.customers_matched or 1248
    else:
        last_run_text = "Never"
        customers_matched = 0

    # Priority alerts (top 3)
    priority_alerts = [a for a in alerts if a['status'] in ['critical', 'reorder_soon']][:3]

    # Campaign activity (recent)
    recent_campaigns = db.query(Campaign).order_by(desc(Campaign.created_at)).limit(3).all()
    campaign_activity = []
    for camp in recent_campaigns:
        clicked_pct = (camp.clicked_count / camp.sent_count * 100) if camp.sent_count > 0 else 0
        campaign_activity.append({
            'id': camp.id,
            'name': camp.name,
            'recipients': camp.total_recipients,
            'sent': camp.sent_count,
            'clicked_pct': round(clicked_pct, 1),
            'status': camp.status
        })

    return {
        'date_range': {
            'start': start_dt.strftime('%Y-%m-%d'),
            'end': end_dt.strftime('%Y-%m-%d')
        },
        'kpis': {
            'forecasted_revenue': round(total_forecast, 0),
            'forecasted_revenue_change': round(revenue_change, 1),
            'items_needing_attention': needs_attention,
            'critical_count': critical_count,
            'reengagement_rate': round(reengagement_rate, 1),
            'reengagement_change': 4.1,
            'campaign_revenue': round(campaign_revenue, 0),
            'campaign_revenue_change': campaign_revenue_change
        },
        'demand_forecast': daily_forecasts,
        'stock_health': stock_health,
        'automation_flow': {
            'last_run': last_run_text,
            'customers_matched': customers_matched,
            'status': last_run.status if last_run else 'idle'
        },
        'priority_alerts': priority_alerts,
        'campaign_activity': campaign_activity
    }

# ============ Inventory Endpoints ============

@app.get("/api/inventory")
async def get_inventory(db: Session = Depends(get_db)):
    """Get all products with forecast data"""
    products = db.query(Product).all()
    alerts = calculate_alerts(db)

    # Create lookup
    alert_map = {a['product_id']: a for a in alerts}

    result = []
    for product in products:
        alert = alert_map.get(product.id, {})
        result.append({
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'price': product.price,
            'current_stock': product.current_stock,
            'daily_velocity': alert.get('daily_velocity', 0),
            'days_to_stockout': alert.get('days_to_stockout', 999),
            'status': alert.get('status', 'healthy'),
            'reorder_point': product.reorder_point,
            'suggested_reorder_qty': alert.get('suggested_reorder_qty', 0)
        })

    return result

@app.post("/api/inventory/{product_id}/restock")
async def restock_product(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db)
):
    """Simulate product restock and trigger cascade"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update stock
    product.current_stock += quantity

    # Log restock
    log = InventoryLog(
        product_id=product_id,
        change_type='restock',
        quantity_change=quantity,
        timestamp=datetime.now(),
        notes=f"Simulated restock of {quantity} units"
    )
    db.add(log)
    db.commit()

    # Trigger cascade
    cascade_result = await trigger_restock_cascade(db, product_id)

    return {
        'success': True,
        'new_stock': product.current_stock,
        'cascade': cascade_result
    }

# ============ Forecast Endpoints ============

@app.get("/api/forecasts")
async def get_all_forecasts(db: Session = Depends(get_db)):
    """Get forecasts for all products"""
    forecasts = calculate_all_forecasts(db)
    return forecasts

@app.get("/api/forecasts/{sku}")
async def get_forecast(sku: str, days: int = 7, db: Session = Depends(get_db)):
    """Get detailed forecast for a specific SKU"""
    product = db.query(Product).filter(Product.sku == sku).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    forecast = calculate_forecast(db, product.id, days_ahead=days)

    # Add historical sales
    historical = db.query(
        func.date(Order.order_date).label('date'),
        func.sum(OrderItem.quantity).label('qty')
    ).join(OrderItem).filter(
        OrderItem.product_id == product.id,
        Order.order_date >= datetime.now() - timedelta(days=30)
    ).group_by(func.date(Order.order_date)).all()

    forecast['historical'] = [
        {'date': str(h.date), 'quantity': float(h.qty)}
        for h in historical
    ]

    return forecast

@app.get("/api/alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """Get all reorder alerts"""
    alerts = calculate_alerts(db)
    return alerts

# ============ Customer Endpoints ============

@app.get("/api/customers")
async def get_customers(db: Session = Depends(get_db)):
    """Get all customers with stats"""
    customers = db.query(Customer).all()

    result = []
    for customer in customers:
        orders = db.query(Order).filter(Order.customer_id == customer.id).all()

        if not orders:
            continue

        total_orders = len(orders)
        last_order = max(orders, key=lambda o: o.order_date)

        # Favorite category
        category_counts = db.query(
            Product.category,
            func.count(OrderItem.id).label('cnt')
        ).join(OrderItem).join(Order).filter(
            Order.customer_id == customer.id
        ).group_by(Product.category).order_by(desc('cnt')).first()

        fav_category = category_counts[0] if category_counts else 'N/A'

        result.append({
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'total_orders': total_orders,
            'last_purchase': last_order.order_date.strftime('%Y-%m-%d'),
            'favorite_category': fav_category,
            'created_at': customer.created_at.strftime('%Y-%m-%d')
        })

    return result

@app.get("/api/customers/{customer_id}")
async def get_customer_detail(customer_id: int, db: Session = Depends(get_db)):
    """Get customer detail with purchase history"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = db.query(Order).filter(Order.customer_id == customer_id).order_by(desc(Order.order_date)).all()

    order_list = []
    for order in orders:
        items = db.query(OrderItem, Product).join(Product).filter(OrderItem.order_id == order.id).all()
        order_list.append({
            'id': order.id,
            'date': order.order_date.strftime('%Y-%m-%d'),
            'channel': order.channel,
            'total': order.total_amount,
            'items': [{'name': p.name, 'qty': oi.quantity, 'price': oi.unit_price} for oi, p in items]
        })

    messages = db.query(Message).filter(Message.customer_id == customer_id).order_by(desc(Message.sent_at)).all()

    return {
        'id': customer.id,
        'name': customer.name,
        'phone': customer.phone,
        'created_at': customer.created_at.strftime('%Y-%m-%d'),
        'orders': order_list,
        'messages_received': len(messages)
    }

# ============ Campaign Endpoints ============

@app.get("/api/campaigns")
async def get_campaigns(db: Session = Depends(get_db)):
    """Get all campaigns"""
    campaigns = db.query(Campaign).order_by(desc(Campaign.created_at)).all()

    result = []
    for camp in campaigns:
        clicked_pct = (camp.clicked_count / camp.sent_count * 100) if camp.sent_count > 0 else 0
        converted_pct = (camp.converted_count / camp.sent_count * 100) if camp.sent_count > 0 else 0

        result.append({
            'id': camp.id,
            'name': camp.name,
            'product_id': camp.product_id,
            'status': camp.status,
            'total_recipients': camp.total_recipients,
            'sent': camp.sent_count,
            'clicked': camp.clicked_count,
            'clicked_pct': round(clicked_pct, 1),
            'converted': camp.converted_count,
            'converted_pct': round(converted_pct, 1),
            'revenue': camp.revenue,
            'created_at': camp.created_at.strftime('%Y-%m-%d %H:%M') if camp.created_at else None,
            'sent_at': camp.sent_at.strftime('%Y-%m-%d %H:%M') if camp.sent_at else None
        })

    return result

@app.post("/api/campaigns")
async def create_campaign(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Create a new campaign for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Match customers
    matches = match_customers_for_product(db, product, limit=500)

    settings = get_settings(db)
    tone = settings.get('message_tone', 'friendly')

    # Create campaign
    campaign = Campaign(
        name=f"Restock: {product.name}",
        product_id=product.id,
        status='review',
        total_recipients=len(matches),
        created_at=datetime.now()
    )
    db.add(campaign)
    db.flush()

    # Create messages
    for match in matches:
        content = generate_message(match['customer_name'], product.name, tone)
        message = Message(
            campaign_id=campaign.id,
            customer_id=match['customer_id'],
            content=content,
            status='pending',
            match_reason=match['reason']
        )
        db.add(message)

    db.commit()

    return {'id': campaign.id, 'status': 'created', 'recipients': len(matches)}

@app.post("/api/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Approve and send a campaign"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = 'sent'
    campaign.sent_at = datetime.now()

    # Update messages
    messages = db.query(Message).filter(Message.campaign_id == campaign_id).all()
    for msg in messages:
        msg.status = 'sent'
        msg.sent_at = datetime.now()

    campaign.sent_count = len(messages)

    # Simulate some engagement
    for msg in random.sample(messages, min(int(len(messages) * 0.25), len(messages))):
        msg.status = 'clicked'
        campaign.clicked_count += 1

    db.commit()

    return {'success': True, 'sent': len(messages)}

# ============ Message Endpoints ============

@app.get("/api/messages")
async def get_messages(db: Session = Depends(get_db)):
    """Get all WhatsApp messages grouped by customer"""
    messages = db.query(Message, Customer, Campaign).join(Customer).join(Campaign).order_by(
        desc(Message.sent_at)
    ).limit(100).all()

    result = []
    for msg, customer, campaign in messages:
        result.append({
            'id': msg.id,
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'customer_id': customer.id,
            'customer_name': customer.name,
            'customer_phone': customer.phone,
            'content': msg.content,
            'status': msg.status,
            'match_reason': msg.match_reason,
            'sent_at': msg.sent_at.strftime('%Y-%m-%d %H:%M:%S') if msg.sent_at else None,
            'delivered_at': msg.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if msg.delivered_at else None,
            'read_at': msg.read_at.strftime('%Y-%m-%d %H:%M:%S') if msg.read_at else None
        })

    return result

@app.post("/api/messages/simulate-delivery")
async def simulate_message_delivery(db: Session = Depends(get_db)):
    """Simulate message delivery progression"""
    # Get pending/sent messages
    messages = db.query(Message).filter(
        Message.status.in_(['sent', 'delivered'])
    ).limit(20).all()

    for msg in messages:
        if msg.status == 'sent':
            msg.status = 'delivered'
            msg.delivered_at = datetime.now()
        elif msg.status == 'delivered' and random.random() < 0.7:
            msg.status = 'read'
            msg.read_at = datetime.now()

    db.commit()

    return {'success': True, 'updated': len(messages)}

# ============ Pipeline Endpoints ============

@app.post("/api/pipeline/run")
async def run_pipeline(db: Session = Depends(get_db)):
    """Trigger the 5-step agentic pipeline"""
    orchestrator = AgentOrchestrator(db)
    run = await orchestrator.run_pipeline()

    return {
        'run_id': run.id,
        'status': run.status,
        'started_at': run.started_at.strftime('%Y-%m-%d %H:%M:%S')
    }

@app.get("/api/pipeline/status")
async def get_pipeline_status(db: Session = Depends(get_db)):
    """Get the latest pipeline run status"""
    run = db.query(PipelineRun).order_by(desc(PipelineRun.started_at)).first()

    if not run:
        return {'status': 'never_run'}

    return {
        'run_id': run.id,
        'status': run.status,
        'current_step': run.current_step,
        'steps': [
            {'number': 1, 'status': run.step_1_status, 'details': run.step_1_details},
            {'number': 2, 'status': run.step_2_status, 'details': run.step_2_details},
            {'number': 3, 'status': run.step_3_status, 'details': run.step_3_details},
            {'number': 4, 'status': run.step_4_status, 'details': run.step_4_details},
            {'number': 5, 'status': run.step_5_status, 'details': run.step_5_details}
        ],
        'customers_matched': run.customers_matched,
        'started_at': run.started_at.strftime('%Y-%m-%d %H:%M:%S'),
        'completed_at': run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if run.completed_at else None
    }

# ============ Settings Endpoints ============

@app.get("/api/settings")
async def get_settings_api(db: Session = Depends(get_db)):
    """Get all settings"""
    settings = get_settings(db)
    return settings

@app.put("/api/settings")
async def update_settings(settings: dict, db: Session = Depends(get_db)):
    """Update settings"""
    for key, value in settings.items():
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            db.add(Settings(key=key, value=str(value)))

    db.commit()
    return {'success': True}

# ============ Upload Endpoints ============

@app.post("/api/upload/sales")
async def upload_sales_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload sales CSV and re-run forecasts"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))

        # Validate columns
        required = ['date', 'sku', 'quantity', 'price']
        if not all(col in df.columns for col in required):
            raise HTTPException(status_code=400, detail=f"CSV must have columns: {required}")

        # Process rows
        added = 0
        for _, row in df.iterrows():
            product = db.query(Product).filter(Product.sku == row['sku']).first()
            if not product:
                continue

            # Create order
            order = Order(
                customer_id=random.choice(db.query(Customer.id).all())[0],
                order_date=datetime.strptime(str(row['date']), '%Y-%m-%d'),
                channel=row.get('channel', 'Online'),
                total_amount=row['price'] * row['quantity']
            )
            db.add(order)
            db.flush()

            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=int(row['quantity']),
                unit_price=float(row['price'])
            )
            db.add(item)
            added += 1

        db.commit()

        return {'success': True, 'rows_added': added}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
