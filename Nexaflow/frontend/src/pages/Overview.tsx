import { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, Package, Users, DollarSign, ArrowRight, MoreHorizontal } from 'lucide-react';
import { api, formatCurrency, getGreeting, openCampaignModal, seedOverview } from '../utils';
import clsx from 'clsx';

export default function Overview() {
  const { user } = useOutletContext<{ user: { businessName: string } }>();
  const [data, setData] = useState<any>(null);
  const [dateRange, setDateRange] = useState('Aug 01 — Aug 16, 2026');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const result = await api.get('/overview');
      setData(result);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load overview:', error);
      setData(seedOverview);
      setLoading(false);
    }
  };

  const runPipeline = async () => {
    try {
      await api.post('/pipeline/run');
      setTimeout(loadData, 2000); // Reload after pipeline runs
    } catch (error) {
      console.error('Failed to run pipeline:', error);
    }
  };

  if (loading || !data) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const automation = data.automation_flow || {};
  const lastRunMinutes = automation.last_run === 'Never' ? null : automation.last_run;

  return (
    <div className="overview-page p-8 space-y-6">
      {/* Header */}
      <div>
        <div className="text-sm font-semibold text-primary mb-2 tracking-wider">
          {getGreeting()}, {user.businessName.toUpperCase()}
        </div>
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2">Operations overview</h1>
            <p className="text-gray-600">
              Turn inventory signals into smarter restocks and repeat sales.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20">
              <option>{dateRange}</option>
            </select>
            <button className="btn-primary flex items-center gap-2" onClick={openCampaignModal}>
              <span className="text-lg">+</span>
              Create campaign
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-6">
        <KPICard
          label="Forecasted revenue"
          value={formatCurrency(data.kpis.forecasted_revenue)}
          change={`↑ ${data.kpis.forecasted_revenue_change}% from last period`}
          iconBg="bg-emerald-100"
          icon={<DollarSign className="w-5 h-5 text-emerald-600" />}
        />
        <KPICard
          label="Items needing attention"
          value={data.kpis.items_needing_attention.toString()}
          change={`${data.kpis.critical_count} critical stock thresholds`}
          iconBg="bg-orange-100"
          icon={<Package className="w-5 h-5 text-orange-600" />}
        />
        <KPICard
          label="Re-engagement rate"
          value={`${data.kpis.reengagement_rate}%`}
          change={`↑ ${data.kpis.reengagement_change}% conversion to purchase`}
          iconBg="bg-blue-100"
          icon={<Users className="w-5 h-5 text-blue-600" />}
        />
        <KPICard
          label="Campaign revenue"
          value={formatCurrency(data.kpis.campaign_revenue)}
          change={`↑ ${data.kpis.campaign_revenue_change}% from WhatsApp`}
          iconBg="bg-purple-100"
          icon={<TrendingUp className="w-5 h-5 text-purple-600" />}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Demand Forecast */}
        <div className="card">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold mb-1">Demand forecast</h3>
              <p className="text-sm text-gray-600">
                Projected order volume for the next 7 days
              </p>
            </div>
            <button className="text-gray-400 hover:text-gray-600">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.demand_forecast}>
              <defs>
                <linearGradient id="colorForecasted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1FA37F" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#1FA37F" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis dataKey="day" stroke="#999" style={{ fontSize: '12px' }} />
              <YAxis stroke="#999" style={{ fontSize: '12px' }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: '13px', paddingTop: '20px' }} />
              <Area
                type="monotone"
                dataKey="forecasted"
                name="Forecasted demand"
                stroke="#1FA37F"
                strokeWidth={2}
                fill="url(#colorForecasted)"
              />
              <Area
                type="monotone"
                dataKey="historical"
                name="Historical average"
                stroke="#94a3b8"
                strokeWidth={1}
                strokeDasharray="5 5"
                fill="none"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Stock Health */}
        <div className="card">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold mb-1">Stock health</h3>
              <p className="text-sm text-gray-600">
                Inventory coverage across all locations
              </p>
            </div>
            <button className="text-gray-400 hover:text-gray-600">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <StockHealthTile
              label="Healthy stock"
              value={`${data.stock_health.healthy}%`}
              color="bg-emerald-500"
            />
            <StockHealthTile
              label="Low stock"
              value={`${data.stock_health.low_stock}%`}
              color="bg-orange-500"
            />
            <StockHealthTile
              label="Out of stock"
              value={`${data.stock_health.out_of_stock}%`}
              color="bg-rose-500"
            />
            <StockHealthTile
              label="Overstocked"
              value={`${data.stock_health.overstocked}%`}
              color="bg-blue-500"
            />
          </div>
          <div className="bg-emerald-50 rounded-lg p-4">
            <p className="text-sm text-emerald-800">
              <span className="font-semibold">{data.stock_health.critical_count + data.stock_health.reorder_soon_count} reorder alerts</span> have been prepared for review today.
            </p>
          </div>
        </div>
      </div>

      {/* Automation Flow */}
      <div className="card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold mb-1">Automation flow</h3>
            <p className="text-sm text-gray-600">
              Your inventory and customer re-engagement engine is running.
            </p>
          </div>
          <button className="text-gray-400 hover:text-gray-600">
            <MoreHorizontal className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-stretch gap-3 mb-4">
          <PipelineStep
            number="01"
            title="Sales data ingested"
            subtitle="POS and online orders synced"
          />
          <ArrowRight className="w-5 h-5 text-gray-300 self-center flex-shrink-0" />
          <PipelineStep
            number="02"
            title="Demand predicted"
            subtitle="Trends and seasonality analysed"
          />
          <ArrowRight className="w-5 h-5 text-gray-300 self-center flex-shrink-0" />
          <PipelineStep
            number="03"
            title="Threshold detected"
            subtitle="18 SKUs need replenishment"
          />
          <ArrowRight className="w-5 h-5 text-gray-300 self-center flex-shrink-0" />
          <PipelineStep
            number="04"
            title="Reorder alert ready"
            subtitle="Awaiting owner approval"
          />
          <ArrowRight className="w-5 h-5 text-gray-300 self-center flex-shrink-0" />
          <PipelineStep
            number="05"
            title="Customers re-engaged"
            subtitle="WhatsApp campaign scheduled"
            highlight
          />
        </div>

        <div className="bg-emerald-50 rounded-lg px-4 py-3 flex items-center justify-between">
          <p className="text-sm text-emerald-800">
            Last successful run: <span className="font-semibold">{lastRunMinutes || 'Never'}</span> · {automation.customers_matched || 0} customers matched for active restock events.
          </p>
          <button
            onClick={runPipeline}
            className="text-sm font-medium text-primary hover:text-primary/80"
          >
            Run now
          </button>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Priority Restock Alerts */}
        <div className="card">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold mb-1">Priority restock alerts</h3>
              <p className="text-sm text-gray-600">
                Products closest to their predicted stock-out date
              </p>
            </div>
            <button className="text-sm font-medium text-primary hover:text-primary/80 flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-3">
            {data.priority_alerts.map((alert: any, i: number) => (
              <AlertRow key={i} alert={alert} />
            ))}
          </div>
        </div>

        {/* Campaign Activity */}
        <div className="card">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold mb-1">Campaign activity</h3>
              <p className="text-sm text-gray-600">
                Latest customer re-engagements
              </p>
            </div>
            <button className="text-gray-400 hover:text-gray-600">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
          <div className="space-y-3">
            {data.campaign_activity.map((campaign: any, i: number) => (
              <CampaignRow key={i} campaign={campaign} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICard({ label, value, change, iconBg, icon }: any) {
  return (
    <div className="card">
      <div className="flex items-start justify-between mb-3">
        <div className="text-sm text-gray-600 font-medium">{label}</div>
        <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', iconBg)}>
          {icon}
        </div>
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm text-emerald-600">{change}</div>
    </div>
  );
}

function StockHealthTile({ label, value, color }: any) {
  return (
    <div>
      <div className="text-sm text-gray-600 mb-2">{label}</div>
      <div className="text-2xl font-bold mb-2">{value}</div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={clsx('h-2 rounded-full', color)} style={{ width: value }}></div>
      </div>
    </div>
  );
}

function PipelineStep({ number, title, subtitle, highlight }: any) {
  return (
    <div className={clsx(
      'flex-1 p-4 rounded-lg border-2',
      highlight ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-gray-200'
    )}>
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold mb-2',
        highlight ? 'bg-emerald-200 text-emerald-800' : 'bg-gray-100 text-gray-600'
      )}>
        {number}
      </div>
      <div className="font-semibold text-sm mb-0.5">{title}</div>
      <div className="text-xs text-gray-600">{subtitle}</div>
    </div>
  );
}

function AlertRow({ alert }: any) {
  const initials = alert.name.split(' ').map((w: string) => w[0]).join('').substring(0, 2);

  return (
    <div className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer">
      <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-sm font-semibold text-gray-600">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm mb-0.5">{alert.name}</div>
        <div className="text-xs text-gray-500">
          SKU {alert.sku} · Predicted stock-out in {alert.days_to_stockout} days
        </div>
      </div>
      <span className={clsx(
        'badge',
        alert.status === 'critical' ? 'badge-critical' : 'badge-warning'
      )}>
        {alert.status === 'critical' ? 'Critical' : 'Reorder soon'}
      </span>
    </div>
  );
}

function CampaignRow({ campaign }: any) {
  const initials = campaign.name.split(' ').map((w: string) => w[0]).join('').substring(0, 2);
  const colors = ['bg-emerald-100', 'bg-blue-100', 'bg-purple-100', 'bg-amber-100'];
  const bgColor = colors[Math.floor(Math.random() * colors.length)];

  return (
    <div className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer">
      <div className={clsx('w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold', bgColor)}>
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm mb-0.5">{campaign.name}</div>
        <div className="text-xs text-gray-500">
          {campaign.recipients > 0
            ? `Sent to ${campaign.recipients} previous buyers`
            : 'Draft campaign ready for approval'}
          {campaign.clicked_pct > 0 && ` · ${campaign.clicked_pct}% clicked`}
        </div>
      </div>
      <span className={clsx(
        'badge',
        campaign.status === 'sent' ? 'badge-success' :
        campaign.status === 'live' ? 'badge-info' :
        'badge-warning'
      )}>
        {campaign.status === 'sent' ? 'Sent' : campaign.status === 'live' ? 'Live' : 'Review'}
      </span>
    </div>
  );
}
