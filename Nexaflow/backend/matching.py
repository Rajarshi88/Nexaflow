import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import Product, Customer, Order, OrderItem, Message, Campaign

def score_customer_for_product(db: Session, customer: Customer, product: Product):
    """
    Score a customer's relevance for a product restock/launch
    Returns (score, reason)
    """
    score = 0
    reasons = []

    # Get customer's order history
    orders = db.query(Order).filter(Order.customer_id == customer.id).all()

    if not orders:
        return 0, "No purchase history"

    # Check for same SKU purchase (high score)
    same_sku_orders = db.query(OrderItem).join(Order).filter(
        Order.customer_id == customer.id,
        OrderItem.product_id == product.id
    ).all()

    if same_sku_orders:
        score += 100
        reasons.append(f"Previously purchased {product.name}")

        # Recency boost
        last_order = db.query(Order).join(OrderItem).filter(
            Order.customer_id == customer.id,
            OrderItem.product_id == product.id
        ).order_by(Order.order_date.desc()).first()

        if last_order:
            days_ago = (datetime.now() - last_order.order_date).days
            if days_ago < 30:
                score += 50
                reasons.append("Recent buyer")
            elif days_ago < 90:
                score += 25

    # Check for same category (medium score)
    same_category_orders = db.query(OrderItem).join(Order).join(Product).filter(
        Order.customer_id == customer.id,
        Product.category == product.category,
        Product.id != product.id
    ).all()

    if same_category_orders and not same_sku_orders:
        score += 50
        reasons.append(f"Bought similar items in {product.category}")

    # Price band matching (customer's average order in similar range)
    customer_avg_price = db.query(func.avg(OrderItem.unit_price)).join(Order).filter(
        Order.customer_id == customer.id
    ).scalar()

    if customer_avg_price:
        price_diff_pct = abs(customer_avg_price - product.price) / product.price
        if price_diff_pct < 0.3:  # Within 30% of their usual spend
            score += 20
            reasons.append("Matches price preference")

    # Check if messaged recently (anti-spam)
    recent_messages = db.query(Message).filter(
        Message.customer_id == customer.id,
        Message.sent_at >= datetime.now() - timedelta(days=7)
    ).count()

    if recent_messages > 0:
        score = 0  # Exclude
        return score, "Messaged in last 7 days"

    reason = "; ".join(reasons) if reasons else "General audience"
    return score, reason

def match_customers_for_product(db: Session, product: Product, limit: int = 500):
    """
    Find and score customers for a product restock/new arrival
    Returns list of (customer, score, reason) sorted by score
    """
    customers = db.query(Customer).all()
    matches = []

    for customer in customers:
        score, reason = score_customer_for_product(db, customer, product)
        if score > 0:
            matches.append({
                'customer_id': customer.id,
                'customer_name': customer.name,
                'customer_phone': customer.phone,
                'score': score,
                'reason': reason
            })

    # Sort by score descending
    matches.sort(key=lambda x: x['score'], reverse=True)

    return matches[:limit]

def generate_message(customer_name: str, product_name: str, tone: str = "friendly"):
    """
    Generate personalized WhatsApp message
    Falls back to templates (Ollama optional)
    """
    first_name = customer_name.split()[0]

    templates = {
        'friendly': [
            f"Hi {first_name}! 🎉 Great news - {product_name} is back in stock! We know you loved it before. Get yours now: nexaflow.shop/p/xyz",
            f"Hey {first_name}! ✨ {product_name} just restocked! Grab it before it's gone again: nexaflow.shop/p/xyz",
            f"{first_name}, your favorite is back! 🛍️ {product_name} available now. Shop here: nexaflow.shop/p/xyz",
            f"Good news, {first_name}! {product_name} is back in stock. Limited quantity available: nexaflow.shop/p/xyz",
            f"Hi {first_name}! We just restocked {product_name} and thought of you 😊 Check it out: nexaflow.shop/p/xyz",
            f"Hey {first_name}! 🌟 {product_name} is available again. Don't miss out this time: nexaflow.shop/p/xyz"
        ],
        'formal': [
            f"Dear {first_name}, We're pleased to inform you that {product_name} is now available. View product: nexaflow.shop/p/xyz",
            f"Hello {first_name}, {product_name} has been restocked. Order now at: nexaflow.shop/p/xyz",
            f"Dear {first_name}, Based on your previous purchase, we thought you'd like to know {product_name} is back in stock: nexaflow.shop/p/xyz",
            f"Hello {first_name}, {product_name} is now available for purchase: nexaflow.shop/p/xyz",
        ]
    }

    tone_templates = templates.get(tone, templates['friendly'])
    return random.choice(tone_templates)
