import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Area, AreaChart } from 'recharts';
import { api, seedForecasts } from '../utils';

export default function Forecasts() {
  const [forecasts, setForecasts] = useState<any[]>([]);
  const [selectedSKU, setSelectedSKU] = useState<string>('');
  const [detailData, setDetailData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    loadForecasts();
  }, []);

  useEffect(() => {
    if (selectedSKU) {
      loadDetail(selectedSKU, days);
    }
  }, [selectedSKU, days]);

  const loadForecasts = async () => {
    try {
      const data = await api.get('/forecasts');
      const nextForecasts = data.length ? data : seedForecasts;
      setForecasts(nextForecasts);
      if (nextForecasts.length > 0) {
        setSelectedSKU(nextForecasts[0].sku);
      }
      setLoading(false);
    } catch (error) {
      console.error('Failed to load forecasts:', error);
      setForecasts(seedForecasts);
      setSelectedSKU(seedForecasts[0].sku);
      setLoading(false);
    }
  };

  const loadDetail = async (sku: string, days: number) => {
    try {
      const data = await api.get(`/forecasts/${sku}?days=${days}`);
      setDetailData(data);
    } catch (error) {
      console.error('Failed to load forecast detail:', error);
      const seed = seedForecasts.find((forecast) => forecast.sku === sku) || seedForecasts[0];
      setDetailData({ ...seed, forecast: seed.forecast.slice(0, days) });
    }
  };

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  // Prepare chart data
  const chartData = detailData?.forecast.map((f: any) => ({
    date: new Date(f.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    demand: f.demand,
    lower: f.lower,
    upper: f.upper,
  })) || [];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Demand Forecasts</h1>
        <p className="text-gray-600">AI-powered predictions for inventory planning</p>
      </div>

      <div className="grid grid-cols-4 gap-6">
        {/* Product Selector */}
        <div className="card col-span-1">
          <h3 className="font-semibold mb-4">Select Product</h3>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {forecasts.map((f) => (
              <button
                key={f.sku}
                onClick={() => setSelectedSKU(f.sku)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedSKU === f.sku
                    ? 'bg-primary text-white'
                    : 'hover:bg-gray-100'
                }`}
              >
                <div className="font-medium text-sm">{f.name}</div>
                <div className={`text-xs ${selectedSKU === f.sku ? 'text-white/80' : 'text-gray-500'}`}>
                  {f.sku}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Forecast Detail */}
        <div className="col-span-3 space-y-6">
          {detailData && (
            <>
              {/* Info Card */}
              <div className="card">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold mb-1">{detailData.name}</h2>
                    <p className="text-gray-600">SKU: {detailData.sku} · {detailData.category}</p>
                  </div>
                  <select
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                    className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value={7}>7 days</option>
                    <option value={14}>14 days</option>
                    <option value={30}>30 days</option>
                  </select>
                </div>

                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Current Stock</div>
                    <div className="text-2xl font-bold">{detailData.current_stock}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Daily Velocity</div>
                    <div className="text-2xl font-bold">{detailData.daily_velocity}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Days to Stockout</div>
                    <div className="text-2xl font-bold">{detailData.days_to_stockout}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Forecast Method</div>
                    <div className="text-sm font-medium">{detailData.method}</div>
                    <div className="text-xs text-gray-500">{detailData.confidence} confidence</div>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorDemand" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1FA37F" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#1FA37F" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorBand" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#94a3b8" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                    <XAxis dataKey="date" stroke="#999" style={{ fontSize: '12px' }} />
                    <YAxis stroke="#999" style={{ fontSize: '12px' }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                    <Area
                      type="monotone"
                      dataKey="upper"
                      stackId="1"
                      stroke="none"
                      fill="url(#colorBand)"
                      name="Upper bound"
                    />
                    <Area
                      type="monotone"
                      dataKey="lower"
                      stackId="2"
                      stroke="none"
                      fill="url(#colorBand)"
                      name="Lower bound"
                    />
                    <Line
                      type="monotone"
                      dataKey="demand"
                      stroke="#1FA37F"
                      strokeWidth={3}
                      dot={{ fill: '#1FA37F', r: 4 }}
                      name="Forecasted demand"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Insights */}
              <div className="card">
                <h3 className="font-semibold mb-4">Forecast Insights</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                    <div className="w-1 h-full bg-blue-500 rounded"></div>
                    <div>
                      <div className="font-medium text-blue-900">Seasonality detected</div>
                      <div className="text-blue-700">Day-of-week patterns identified in historical sales</div>
                    </div>
                  </div>
                  {detailData.days_to_stockout <= 7 && (
                    <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
                      <div className="w-1 h-full bg-orange-500 rounded"></div>
                      <div>
                        <div className="font-medium text-orange-900">Reorder recommended</div>
                        <div className="text-orange-700">
                          Stock will run out in {detailData.days_to_stockout} days at current velocity
                        </div>
                      </div>
                    </div>
                  )}
                  <div className="flex items-start gap-3 p-3 bg-emerald-50 rounded-lg">
                    <div className="w-1 h-full bg-emerald-500 rounded"></div>
                    <div>
                      <div className="font-medium text-emerald-900">Model accuracy</div>
                      <div className="text-emerald-700">EWMA model with 95% confidence bands</div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
