export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export type DemoUser = { businessName: string; email: string };

export const seedCustomers = [
  { id: 1, name: 'Ananya Sharma', phone: '+91 98765 43210', total_orders: 12, favorite_category: 'Beverages', last_purchase: '2026-08-14', created_at: '2025-11-04' },
  { id: 2, name: 'Rohan Mehta', phone: '+91 98204 11772', total_orders: 8, favorite_category: 'Snacks', last_purchase: '2026-08-12', created_at: '2026-01-18' },
  { id: 3, name: 'Priya Nair', phone: '+91 98470 22518', total_orders: 16, favorite_category: 'Personal care', last_purchase: '2026-08-10', created_at: '2025-08-22' },
  { id: 4, name: 'Kabir Singh', phone: '+91 98100 77542', total_orders: 6, favorite_category: 'Household', last_purchase: '2026-08-08', created_at: '2026-03-11' },
  { id: 5, name: 'Meera Iyer', phone: '+91 99001 64522', total_orders: 10, favorite_category: 'Beverages', last_purchase: '2026-08-06', created_at: '2025-12-20' },
];

export const seedInventory = [
  { id: 1, sku: '01-DS-CRM', name: 'Summer Dress — Coral', category: 'Apparel', price: 2499, current_stock: 3, daily_velocity: 1.5, days_to_stockout: 2, status: 'critical', reorder_point: 13, suggested_reorder_qty: 50 },
  { id: 2, sku: '04-TEE-BLK', name: 'Classic Black Tee', category: 'Apparel', price: 599, current_stock: 6, daily_velocity: 1.4, days_to_stockout: 4, status: 'reorder_soon', reorder_point: 36, suggested_reorder_qty: 50 },
  { id: 3, sku: '11-FRG-SIG', name: 'Signature Scent 50ml', category: 'Fragrance', price: 3999, current_stock: 9, daily_velocity: 1.7, days_to_stockout: 5, status: 'reorder_soon', reorder_point: 10, suggested_reorder_qty: 35 },
  { id: 4, sku: '21-BAG-LTH', name: 'Leather Handbag', category: 'Accessories', price: 5999, current_stock: 22, daily_velocity: 0.5, days_to_stockout: 44, status: 'healthy', reorder_point: 10, suggested_reorder_qty: 20 },
  { id: 5, sku: '31-HOM-CND', name: 'Scented Candle Set', category: 'Home', price: 1799, current_stock: 68, daily_velocity: 0.8, days_to_stockout: 85, status: 'overstocked', reorder_point: 20, suggested_reorder_qty: 0 },
];

export const seedForecasts = seedInventory.map((product) => ({
  sku: product.sku,
  name: product.name,
  category: product.category,
  current_stock: product.current_stock,
  daily_velocity: product.daily_velocity,
  days_to_stockout: product.days_to_stockout,
  method: 'EWMA',
  confidence: 'High',
  forecast: Array.from({ length: 14 }, (_, index) => {
    const demand = Math.max(1, Math.round(product.daily_velocity * (1 + ((index % 4) - 1) * 0.08) * 10) / 10);
    return { date: `2026-08-${String(17 + index).padStart(2, '0')}`, demand, lower: Math.max(0, demand - 1.2), upper: demand + 1.8 };
  }),
}));

export const seedCampaigns = [
  { id: 101, name: 'Summer Dress restock', status: 'sent', total_recipients: 38, sent: 38, clicked: 12, clicked_pct: 31.6, converted: 5, converted_pct: 13.2, revenue: 4820, created_at: '2026-08-15 09:30', sent_at: '2026-08-15 09:35' },
  { id: 102, name: 'Signature Scent restock', status: 'review', total_recipients: 24, sent: 0, clicked: 0, clicked_pct: 0, converted: 0, converted_pct: 0, revenue: 0, created_at: '2026-08-16 08:15', sent_at: null },
];

export const seedMessages = [
  { id: 1, campaign_id: 101, campaign_name: 'Summer Dress restock', customer_id: 1, customer_name: 'Ananya Sharma', customer_phone: '+91 98765 43210', content: 'Hi Ananya, Summer Dress — Coral is back in stock. We saved one for you.', status: 'clicked', match_reason: 'Purchased this SKU twice recently', sent_at: '2026-08-15 09:35:00' },
  { id: 2, campaign_id: 101, campaign_name: 'Summer Dress restock', customer_id: 5, customer_name: 'Meera Iyer', customer_phone: '+91 99001 64522', content: 'Hi Meera, your favourite Summer Dress — Coral is available again.', status: 'delivered', match_reason: 'Repeat beverage customer', sent_at: '2026-08-15 09:35:00' },
];

export const seedOverview = {
  kpis: { forecasted_revenue: 184500, forecasted_revenue_change: 12.4, items_needing_attention: 4, critical_count: 2, reengagement_rate: 24.8, reengagement_change: 4.1, campaign_revenue: 48200, campaign_revenue_change: 18.7 },
  demand_forecast: [{ day: 'Mon', forecasted: 128, historical: 104 }, { day: 'Tue', forecasted: 142, historical: 121 }, { day: 'Wed', forecasted: 156, historical: 130 }, { day: 'Thu', forecasted: 149, historical: 126 }, { day: 'Fri', forecasted: 176, historical: 142 }, { day: 'Sat', forecasted: 191, historical: 158 }, { day: 'Sun', forecasted: 168, historical: 151 }],
  stock_health: { healthy: 62, low_stock: 20, out_of_stock: 8, overstocked: 10, critical_count: 2, reorder_soon_count: 2 },
  automation_flow: { last_run: '18 minutes ago', customers_matched: 1248, status: 'completed' },
  priority_alerts: [{ product_name: 'Summer Dress — Coral', sku: 'BEV-001', status: 'critical', days_to_stockout: 3 }, { product_name: 'Sea Salt Almonds', sku: 'SNK-014', status: 'reorder_soon', days_to_stockout: 9 }],
  campaign_activity: [{ id: 101, name: 'Summer Dress restock', recipients: 38, sent: 38, clicked_pct: 31.6, status: 'sent' }, { id: 102, name: 'Signature Scent restock', recipients: 24, sent: 0, clicked_pct: 0, status: 'review' }],
};

async function request(endpoint: string, options?: RequestInit) {
  const controller = new AbortController();
  // Dev tunnels and Brevo HTTPS delivery can take longer than a local request.
  // Keep the request alive long enough for the backend to send the OTP.
  const timeout = window.setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, { ...options, signal: controller.signal });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The backend took too long to respond. Check that the backend tunnel is running and try again.');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  async get(endpoint: string) { return request(endpoint); },
  async post(endpoint: string, data?: unknown) { return request(endpoint, { method: 'POST', headers: data ? { 'Content-Type': 'application/json' } : undefined, body: data ? JSON.stringify(data) : undefined }); },
  async put(endpoint: string, data: unknown) { return request(endpoint, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); },
};

export function openCampaignModal() { window.dispatchEvent(new CustomEvent('nexaflow:open-campaign')); }
export function formatCurrency(value: number): string { if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)}Cr`; if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`; if (value >= 1000) return `₹${(value / 1000).toFixed(2)}K`; return `₹${value.toFixed(0)}`; }
export function getGreeting(): string { const hour = new Date().getHours(); if (hour < 12) return 'GOOD MORNING'; if (hour < 17) return 'GOOD AFTERNOON'; return 'GOOD EVENING'; }
