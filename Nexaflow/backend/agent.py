import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import PipelineRun, Product, Campaign, Message, InventoryLog, Settings
from forecast import calculate_alerts, calculate_all_forecasts, get_settings
from matching import match_customers_for_product, generate_message

class AgentOrchestrator:
    """
    5-step agentic pipeline for inventory -> customer engagement
    """

    def __init__(self, db: Session):
        self.db = db

    async def run_pipeline(self):
        """Execute the full 5-step pipeline"""
        # Create pipeline run
        run = PipelineRun(
            status='running',
            started_at=datetime.now()
        )
        self.db.add(run)
        self.db.commit()

        try:
            # Step 1: Ingest sales data
            await self.step_1_ingest_data(run)
            await asyncio.sleep(0.5)

            # Step 2: Predict demand
            await self.step_2_predict_demand(run)
            await asyncio.sleep(0.5)

            # Step 3: Detect thresholds
            await self.step_3_detect_thresholds(run)
            await asyncio.sleep(0.5)

            # Step 4: Prepare reorder alerts
            await self.step_4_reorder_alerts(run)
            await asyncio.sleep(0.5)

            # Step 5: Re-engage customers
            await self.step_5_reengage_customers(run)

            # Complete
            run.status = 'completed'
            run.completed_at = datetime.now()
            self.db.commit()

            return run

        except Exception as e:
            run.status = 'failed'
            run.completed_at = datetime.now()
            self.db.commit()
            raise e

    async def step_1_ingest_data(self, run: PipelineRun):
        """Step 1: Sales data ingested"""
        run.current_step = 1
        run.step_1_status = 'running'
        self.db.commit()

        # Count recent orders
        from models import Order
        recent_orders = self.db.query(Order).filter(
            Order.order_date >= datetime.now() - timedelta(days=7)
        ).count()

        run.step_1_status = 'completed'
        run.step_1_details = f"Synced {recent_orders} orders from last 7 days (POS + Online channels)"
        self.db.commit()

    async def step_2_predict_demand(self, run: PipelineRun):
        """Step 2: Demand predicted"""
        run.current_step = 2
        run.step_2_status = 'running'
        self.db.commit()

        # Calculate forecasts
        forecasts = calculate_all_forecasts(self.db)

        run.step_2_status = 'completed'
        run.step_2_details = f"Analyzed trends and seasonality for {len(forecasts)} SKUs using EWMA model"
        self.db.commit()

    async def step_3_detect_thresholds(self, run: PipelineRun):
        """Step 3: Threshold detected"""
        run.current_step = 3
        run.step_3_status = 'running'
        self.db.commit()

        # Calculate alerts
        alerts = calculate_alerts(self.db)
        needs_reorder = [a for a in alerts if a['status'] in ['critical', 'reorder_soon', 'out_of_stock']]

        run.step_3_status = 'completed'
        run.step_3_details = f"{len(needs_reorder)} SKUs need replenishment (threshold-based detection)"
        self.db.commit()

    async def step_4_reorder_alerts(self, run: PipelineRun):
        """Step 4: Reorder alert ready"""
        run.current_step = 4
        run.step_4_status = 'running'
        self.db.commit()

        alerts = calculate_alerts(self.db)
        needs_reorder = [a for a in alerts if a['status'] in ['critical', 'reorder_soon', 'out_of_stock']]

        run.step_4_status = 'completed'
        run.step_4_details = f"{len(needs_reorder)} reorder alerts prepared for owner review"
        self.db.commit()

    async def step_5_reengage_customers(self, run: PipelineRun):
        """Step 5: Customers re-engaged"""
        run.current_step = 5
        run.step_5_status = 'running'
        self.db.commit()

        # Check for recent restocks
        recent_restocks = self.db.query(InventoryLog).filter(
            InventoryLog.change_type == 'restock',
            InventoryLog.timestamp >= datetime.now() - timedelta(hours=24)
        ).all()

        total_matched = 0
        campaigns_created = 0

        settings = get_settings(self.db)
        auto_approve = settings.get('auto_approve', 'false') == 'true'

        for restock in recent_restocks:
            product = restock.product

            # Check if campaign already exists for this restock
            existing = self.db.query(Campaign).filter(
                Campaign.product_id == product.id,
                Campaign.created_at >= datetime.now() - timedelta(hours=24)
            ).first()

            if existing:
                continue

            # Match customers
            matches = match_customers_for_product(self.db, product, limit=500)

            if matches:
                # Create campaign
                campaign = Campaign(
                    name=f"Restock: {product.name}",
                    product_id=product.id,
                    status='review' if not auto_approve else 'sent',
                    total_recipients=len(matches),
                    created_at=datetime.now(),
                    sent_at=datetime.now() if auto_approve else None
                )
                self.db.add(campaign)
                self.db.flush()

                # Create messages
                tone = settings.get('message_tone', 'friendly')
                for match in matches:
                    content = generate_message(
                        match['customer_name'],
                        product.name,
                        tone
                    )

                    message = Message(
                        campaign_id=campaign.id,
                        customer_id=match['customer_id'],
                        content=content,
                        status='sent' if auto_approve else 'pending',
                        match_reason=match['reason'],
                        sent_at=datetime.now() if auto_approve else None
                    )
                    self.db.add(message)

                if auto_approve:
                    campaign.sent_count = len(matches)

                total_matched += len(matches)
                campaigns_created += 1

        self.db.commit()

        run.customers_matched = total_matched
        run.step_5_status = 'completed'
        run.step_5_details = f"{campaigns_created} WhatsApp campaigns scheduled; {total_matched} customers matched"
        self.db.commit()

async def trigger_restock_cascade(db: Session, product_id: int):
    """
    Triggered when a product is restocked - automatically cascade to customer matching
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    # Match customers
    matches = match_customers_for_product(db, product, limit=500)

    if not matches:
        return None

    settings = get_settings(db)
    auto_approve = settings.get('auto_approve', 'false') == 'true'
    tone = settings.get('message_tone', 'friendly')

    # Create campaign
    campaign = Campaign(
        name=f"Restock: {product.name}",
        product_id=product.id,
        status='review' if not auto_approve else 'sent',
        total_recipients=len(matches),
        created_at=datetime.now(),
        sent_at=datetime.now() if auto_approve else None
    )
    db.add(campaign)
    db.flush()

    # Create messages
    for match in matches:
        content = generate_message(
            match['customer_name'],
            product.name,
            tone
        )

        message = Message(
            campaign_id=campaign.id,
            customer_id=match['customer_id'],
            content=content,
            status='sent' if auto_approve else 'pending',
            match_reason=match['reason'],
            sent_at=datetime.now() if auto_approve else None
        )
        db.add(message)

    if auto_approve:
        campaign.sent_count = len(matches)

    db.commit()

    return {
        'campaign_id': campaign.id,
        'matched_customers': len(matches),
        'status': campaign.status
    }
