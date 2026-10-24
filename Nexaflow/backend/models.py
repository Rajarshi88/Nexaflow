from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    current_stock = Column(Integer, default=0)
    reorder_point = Column(Integer, default=0)
    lead_time_days = Column(Integer, default=3)

    order_items = relationship("OrderItem", back_populates="product")
    inventory_logs = relationship("InventoryLog", back_populates="product")
    forecasts = relationship("Forecast", back_populates="product")

class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")
    messages = relationship("Message", back_populates="customer")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    order_date = Column(DateTime, nullable=False)
    channel = Column(String(50), default='POS')  # POS or Online
    total_amount = Column(Float, default=0)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class InventoryLog(Base):
    __tablename__ = 'inventory_logs'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    change_type = Column(String(50), nullable=False)  # restock, sale, adjustment
    quantity_change = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

    product = relationship("Product", back_populates="inventory_logs")

class Forecast(Base):
    __tablename__ = 'forecasts'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    forecast_date = Column(DateTime, nullable=False)
    predicted_demand = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=False)
    confidence_upper = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="forecasts")

class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    status = Column(String(50), default='draft')  # draft, review, live, sent
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    converted_count = Column(Integer, default=0)
    revenue = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    content = Column(Text, nullable=False)
    status = Column(String(50), default='pending')  # pending, sent, delivered, read, clicked
    match_reason = Column(String(200))
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="messages")

class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'

    id = Column(Integer, primary_key=True)
    status = Column(String(50), default='running')  # running, completed, failed
    current_step = Column(Integer, default=1)
    step_1_status = Column(String(50), default='pending')
    step_1_details = Column(Text)
    step_2_status = Column(String(50), default='pending')
    step_2_details = Column(Text)
    step_3_status = Column(String(50), default='pending')
    step_3_details = Column(Text)
    step_4_status = Column(String(50), default='pending')
    step_4_details = Column(Text)
    step_5_status = Column(String(50), default='pending')
    step_5_details = Column(Text)
    customers_matched = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)

class SignupOtp(Base):
    __tablename__ = 'signup_otps'

    id = Column(Integer, primary_key=True)
    email = Column(String(320), nullable=False, index=True)
    business_name = Column(String(200), nullable=False)
    otp_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# Database setup
engine = create_engine('sqlite:///nexaflow.db', echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
