import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Product, Order, OrderItem, Forecast, Settings

def get_settings(db: Session):
    """Get settings as dict"""
    settings_list = db.query(Settings).all()
    return {s.key: s.value for s in settings_list}

def calculate_forecast(db: Session, product_id: int, days_ahead: int = 7):
    """
    Calculate demand forecast for a product using EWMA + seasonality
    Returns forecast data with confidence bands
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    # Get historical sales data (last 90 days)
    ninety_days_ago = datetime.now() - timedelta(days=90)

    order_items = db.query(
        Order.order_date,
        OrderItem.quantity
    ).join(OrderItem).filter(
        OrderItem.product_id == product_id,
        Order.order_date >= ninety_days_ago
    ).all()

    if not order_items:
        # No history - return flat forecast
        return {
            'sku': product.sku,
            'name': product.name,
            'forecast': [{'date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
                         'demand': 0, 'lower': 0, 'upper': 0} for i in range(days_ahead)],
            'current_stock': product.current_stock,
            'method': 'No historical data'
        }

    # Create daily series
    df = pd.DataFrame(order_items, columns=['date', 'quantity'])
    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.date

    daily_sales = df.groupby('date')['quantity'].sum().reset_index()
    daily_sales.columns = ['date', 'qty']

    # Fill missing dates with 0
    date_range = pd.date_range(
        start=ninety_days_ago.date(),
        end=datetime.now().date(),
        freq='D'
    )
    full_series = pd.DataFrame({'date': date_range.date})
    daily_sales = full_series.merge(daily_sales, on='date', how='left').fillna(0)

    # Calculate day-of-week seasonality
    daily_sales['date'] = pd.to_datetime(daily_sales['date'])
    daily_sales['dow'] = daily_sales['date'].dt.dayofweek
    dow_avg = daily_sales.groupby('dow')['qty'].mean()
    overall_avg = daily_sales['qty'].mean()
    dow_factor = (dow_avg / overall_avg).fillna(1.0) if overall_avg > 0 else pd.Series([1.0] * 7)

    # EWMA for trend
    alpha = 0.3
    ewma = daily_sales['qty'].ewm(alpha=alpha, adjust=False).mean()
    base_forecast = ewma.iloc[-1] if len(ewma) > 0 else overall_avg

    # Calculate residual std for confidence bands
    residuals = daily_sales['qty'] - ewma
    std_residual = residuals.std() if len(residuals) > 1 else base_forecast * 0.3

    # Generate forecasts
    forecasts = []
    for i in range(days_ahead):
        future_date = datetime.now() + timedelta(days=i+1)
        dow = future_date.weekday()
        seasonal_factor = dow_factor.get(dow, 1.0)

        predicted = base_forecast * seasonal_factor
        lower = max(0, predicted - 1.96 * std_residual)
        upper = predicted + 1.96 * std_residual

        forecasts.append({
            'date': future_date.strftime('%Y-%m-%d'),
            'demand': round(float(predicted), 2),
            'lower': round(float(lower), 2),
            'upper': round(float(upper), 2)
        })

    # Calculate days to stockout
    cumulative = 0
    days_to_stockout = None
    for i, f in enumerate(forecasts):
        cumulative += f['demand']
        if cumulative >= product.current_stock and days_to_stockout is None:
            days_to_stockout = i + 1

    if days_to_stockout is None:
        days_to_stockout = days_ahead + 1  # Beyond forecast window

    # Calculate daily velocity and accuracy
    recent_7_days = daily_sales.tail(7)['qty'].mean()

    return {
        'sku': product.sku,
        'name': product.name,
        'category': product.category,
        'current_stock': product.current_stock,
        'forecast': forecasts,
        'days_to_stockout': days_to_stockout,
        'daily_velocity': round(float(recent_7_days), 2),
        'method': 'EWMA + Day-of-week seasonality',
        'confidence': '95%'
    }

def calculate_all_forecasts(db: Session):
    """Calculate forecasts for all products"""
    products = db.query(Product).all()
    results = []

    for product in products:
        forecast_data = calculate_forecast(db, product.id, days_ahead=7)
        if forecast_data:
            results.append(forecast_data)

    return results

def calculate_alerts(db: Session):
    """Calculate reorder alerts based on forecasts and thresholds"""
    settings = get_settings(db)
    lead_time = int(settings.get('lead_time_days', 3))
    safety_stock_pct = float(settings.get('safety_stock_percent', 20))
    critical_days = int(settings.get('critical_threshold_days', 3))
    reorder_days = int(settings.get('reorder_threshold_days', 7))

    products = db.query(Product).all()
    alerts = []

    for product in products:
        forecast_data = calculate_forecast(db, product.id, days_ahead=14)
        if not forecast_data:
            continue

        days_to_stockout = forecast_data['days_to_stockout']
        daily_velocity = forecast_data['daily_velocity']

        # Determine status
        status = 'healthy'
        priority = 3

        if product.current_stock == 0:
            status = 'out_of_stock'
            priority = 0
        elif days_to_stockout <= critical_days:
            status = 'critical'
            priority = 1
        elif days_to_stockout <= reorder_days:
            status = 'reorder_soon'
            priority = 2
        elif days_to_stockout > 60:
            status = 'overstocked'
            priority = 4

        # Calculate suggested reorder quantity
        safety_stock = daily_velocity * lead_time * (safety_stock_pct / 100)
        suggested_qty = int(daily_velocity * (lead_time + 14) + safety_stock - product.current_stock)
        suggested_qty = max(0, suggested_qty)

        # Reason
        reason = f"Predicted stock-out in {days_to_stockout} days; lead time {lead_time} days"
        if status == 'critical':
            reason += " → reorder now"
        elif status == 'out_of_stock':
            reason = "Out of stock - immediate reorder required"

        alerts.append({
            'product_id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': product.current_stock,
            'daily_velocity': daily_velocity,
            'days_to_stockout': days_to_stockout,
            'status': status,
            'priority': priority,
            'suggested_reorder_qty': suggested_qty,
            'reason': reason
        })

    # Sort by priority then days to stockout
    alerts.sort(key=lambda x: (x['priority'], x['days_to_stockout']))

    return alerts

def calculate_stock_health(db: Session):
    """Calculate stock health distribution"""
    alerts = calculate_alerts(db)
    total = len(alerts)

    if total == 0:
        return {
            'healthy': 0, 'low_stock': 0,
            'out_of_stock': 0, 'overstocked': 0
        }

    counts = {
        'out_of_stock': len([a for a in alerts if a['status'] == 'out_of_stock']),
        'critical': len([a for a in alerts if a['status'] == 'critical']),
        'reorder_soon': len([a for a in alerts if a['status'] == 'reorder_soon']),
        'overstocked': len([a for a in alerts if a['status'] == 'overstocked']),
    }
    counts['healthy'] = total - sum(counts.values())

    return {
        'healthy': round(counts['healthy'] / total * 100, 1),
        'low_stock': round((counts['critical'] + counts['reorder_soon']) / total * 100, 1),
        'out_of_stock': round(counts['out_of_stock'] / total * 100, 1),
        'overstocked': round(counts['overstocked'] / total * 100, 1),
        'critical_count': counts['critical'],
        'reorder_soon_count': counts['reorder_soon']
    }
