import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from models import (
    init_db, SessionLocal, Product, Customer, Order, OrderItem,
    InventoryLog, Settings, Campaign, Message
)

random.seed(42)
np.random.seed(42)

# Indian names
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Arnav", "Ayaan", "Krishna", "Ishaan",
    "Aadhya", "Ananya", "Diya", "Isha", "Priya", "Saanvi", "Sara", "Kavya", "Anika", "Riya",
    "Rohan", "Aryan", "Kabir", "Advait", "Ved", "Shivansh", "Reyansh", "Dhruv", "Atharv", "Yash",
    "Kiara", "Avni", "Myra", "Tara", "Siya", "Navya", "Mira", "Aarohi", "Pari", "Nisha",
    "Rajesh", "Amit", "Suresh", "Vikram", "Nikhil", "Rahul", "Karan", "Varun", "Gaurav", "Sandeep"
]

LAST_NAMES = [
    "Sharma", "Verma", "Singh", "Kumar", "Patel", "Gupta", "Reddy", "Shah", "Nair", "Menon",
    "Desai", "Joshi", "Kulkarni", "Iyer", "Chopra", "Mehta", "Agarwal", "Malhotra", "Bansal", "Kapoor"
]

CATEGORIES = {
    "Apparel": [
        ("Summer Dress — Coral", "01-DS-CRM", 2499, 45),
        ("Summer Dress — Navy", "01-DS-NVY", 2499, 38),
        ("Classic Black Tee", "04-TEE-BLK", 599, 120),
        ("White Cotton Tee", "04-TEE-WHT", 599, 95),
        ("Linen Co-ord Set", "02-CRD-LIN", 3499, 28),
        ("Denim Jacket", "05-JKT-DNM", 4999, 15),
        ("Floral Midi Skirt", "03-SKT-FLR", 1899, 42),
        ("Casual Joggers", "06-JOG-GRY", 1299, 65),
        ("Silk Saree", "07-SAR-SLK", 8999, 12),
        ("Cotton Kurta", "08-KRT-CTN", 1799, 55)
    ],
    "Fragrance": [
        ("Signature Scent 50ml", "11-FRG-SIG", 3999, 32),
        ("Fresh Citrus 100ml", "11-FRG-CTR", 2999, 48),
        ("Rose Garden 50ml", "11-FRG-RSE", 4499, 25),
        ("Woody Musk 100ml", "11-FRG-MSK", 5499, 18)
    ],
    "Accessories": [
        ("Leather Handbag", "21-BAG-LTH", 5999, 22),
        ("Canvas Tote", "21-BAG-CNV", 1499, 58),
        ("Silver Earrings", "22-JWL-ERG", 2999, 35),
        ("Pendant Necklace", "22-JWL-NKL", 3499, 28),
        ("Sunglasses Classic", "23-SUN-CLS", 1999, 45),
        ("Leather Belt", "24-BLT-LTH", 1299, 52)
    ],
    "Home": [
        ("Scented Candle Set", "31-HOM-CND", 1799, 68),
        ("Cotton Bedsheet", "32-HOM-BED", 2499, 35),
        ("Ceramic Vase", "33-HOM-VSE", 1499, 42),
        ("Cushion Cover Set", "34-HOM-CSH", 999, 78),
        ("Wall Art Print", "35-HOM-ART", 1999, 25),
        ("Bamboo Organizer", "36-HOM-ORG", 1299, 48),
        ("Aromatherapy Diffuser", "37-HOM-DIF", 2999, 30),
        ("Table Runner", "38-HOM-TBL", 899, 55),
        ("Photo Frame Set", "39-HOM-FRM", 1499, 38)
    ]
}

def generate_phone():
    """Generate fake Indian phone number"""
    return f"+91 9{random.randint(100000000, 999999999)}"

def seed_database():
    print("Initializing database...")
    init_db()

    db = SessionLocal()

    # Clear existing data
    print("Clearing existing data...")
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Message).delete()
    db.query(Campaign).delete()
    db.query(InventoryLog).delete()
    db.query(Customer).delete()
    db.query(Product).delete()
    db.query(Settings).delete()
    db.commit()

    # Seed settings
    print("Seeding settings...")
    settings = [
        Settings(key="lead_time_days", value="3"),
        Settings(key="safety_stock_percent", value="20"),
        Settings(key="critical_threshold_days", value="3"),
        Settings(key="reorder_threshold_days", value="7"),
        Settings(key="message_tone", value="friendly"),
        Settings(key="auto_approve", value="false"),
    ]
    db.add_all(settings)
    db.commit()

    # Seed products
    print("Seeding products...")
    products = []
    for category, items in CATEGORIES.items():
        for name, sku, price, base_stock in items:
            product = Product(
                sku=sku,
                name=name,
                category=category,
                price=price,
                current_stock=base_stock,
                reorder_point=max(10, int(base_stock * 0.3)),
                lead_time_days=3
            )
            products.append(product)
            db.add(product)

    db.commit()
    print(f"Created {len(products)} products")

    # Seed customers
    print("Seeding customers...")
    customers = []
    for _ in range(1500):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        customer = Customer(
            name=f"{first} {last}",
            phone=generate_phone(),
            created_at=datetime.now() - timedelta(days=random.randint(180, 730))
        )
        customers.append(customer)
        db.add(customer)

    db.commit()
    print(f"Created {len(customers)} customers")

    # Seed orders (12 months of history)
    print("Seeding orders...")
    start_date = datetime.now() - timedelta(days=365)
    current_date = start_date

    # Seasonal factors
    def get_seasonal_factor(date):
        month = date.month
        day_of_week = date.weekday()

        # Weekly pattern (higher on weekends)
        weekly_factor = 1.3 if day_of_week in [5, 6] else 1.0

        # Monthly pattern
        monthly_factors = {
            1: 0.8,   # Jan
            2: 0.85,  # Feb
            3: 1.1,   # Mar (spring)
            4: 1.2,   # Apr
            5: 1.3,   # May
            6: 1.1,   # Jun
            7: 0.9,   # Jul
            8: 1.4,   # Aug (festive - Raksha Bandhan)
            9: 1.0,   # Sep
            10: 1.5,  # Oct (Diwali)
            11: 1.6,  # Nov (Diwali season)
            12: 1.2   # Dec
        }

        return weekly_factor * monthly_factors.get(month, 1.0)

    order_count = 0
    while current_date <= datetime.now():
        seasonal = get_seasonal_factor(current_date)
        base_orders = int(8 * seasonal)  # Average 8 orders per day, adjusted
        daily_orders = max(2, np.random.poisson(base_orders))

        for _ in range(daily_orders):
            customer = random.choice(customers)
            channel = random.choices(["POS", "Online"], weights=[0.6, 0.4])[0]

            order = Order(
                customer_id=customer.id,
                order_date=current_date + timedelta(
                    hours=random.randint(9, 20),
                    minutes=random.randint(0, 59)
                ),
                channel=channel
            )
            db.add(order)
            db.flush()

            # Add 1-4 items per order
            num_items = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]
            selected_products = random.sample(products, num_items)

            total = 0
            for product in selected_products:
                qty = random.randint(1, 3)

                # Category seasonality
                if product.category == "Apparel":
                    if current_date.month in [3, 4, 5, 6]:  # Summer
                        if "Summer" in product.name or "Tee" in product.name:
                            qty = random.randint(1, 4)

                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.price
                )
                db.add(item)
                total += qty * product.price

            order.total_amount = total
            order_count += 1

        current_date += timedelta(days=1)

    db.commit()
    print(f"Created {order_count} orders")

    # Seed a small campaign and message history so the engagement pages
    # have real database-backed demo data on the first run.
    print("Seeding campaigns and messages...")
    campaign_product = products[0]
    audience = customers[:12]
    sent_campaign = Campaign(
        name=f"{campaign_product.name} restock",
        product_id=campaign_product.id,
        status='sent',
        total_recipients=len(audience),
        sent_count=len(audience),
        clicked_count=4,
        converted_count=2,
        revenue=9996,
        created_at=datetime.now() - timedelta(days=2),
        sent_at=datetime.now() - timedelta(days=2, minutes=-5)
    )
    review_campaign = Campaign(
        name="New arrivals audience",
        product_id=products[1].id,
        status='review',
        total_recipients=8,
        created_at=datetime.now() - timedelta(hours=4)
    )
    db.add_all([sent_campaign, review_campaign])
    db.flush()
    for index, customer in enumerate(audience):
        db.add(Message(
            campaign_id=sent_campaign.id,
            customer_id=customer.id,
            content=f"Hi {customer.name.split()[0]}, {campaign_product.name} is back in stock. We saved one for you.",
            status='clicked' if index < 4 else 'delivered',
            match_reason='Purchased this product or category recently',
            sent_at=datetime.now() - timedelta(days=2, minutes=index)
        ))
    db.commit()
    print(f"Created {2} campaigns and {len(audience)} messages")

    # Calculate and update current stock based on order history
    print("Calculating current stock levels...")
    for product in products:
        # Get total sold in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        total_sold = db.query(OrderItem).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.order_date >= thirty_days_ago
        ).with_entities(OrderItem.quantity).all()

        sold_qty = sum([x[0] for x in total_sold]) if total_sold else 0

        # Calculate velocity and stock
        daily_velocity = sold_qty / 30

        # Engineer specific SKUs to match requirements
        if product.sku == "01-DS-CRM":  # 2 days to stockout - Critical
            product.current_stock = int(daily_velocity * 2.2)
        elif product.sku == "04-TEE-BLK":  # 4 days
            product.current_stock = int(daily_velocity * 4.3)
        elif product.sku == "11-FRG-SIG":  # 5 days
            product.current_stock = int(daily_velocity * 5.1)
        else:
            # Random distribution for others
            rand = random.random()
            if rand < 0.04:  # 4% out of stock
                product.current_stock = 0
            elif rand < 0.23:  # 19% low stock
                product.current_stock = int(daily_velocity * random.uniform(3, 7))
            elif rand < 0.28:  # 5% overstocked
                product.current_stock = int(daily_velocity * random.uniform(60, 90))
            else:  # 72% healthy
                product.current_stock = int(daily_velocity * random.uniform(15, 45))

        product.current_stock = max(0, product.current_stock)

    db.commit()

    print("Database seeded successfully!")
    print(f"   Products: {len(products)}")
    print(f"   Customers: {len(customers)}")
    print(f"   Orders: {order_count}")

    db.close()

if __name__ == "__main__":
    seed_database()
