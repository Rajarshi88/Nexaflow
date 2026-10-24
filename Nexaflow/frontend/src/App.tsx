import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Layout from './components/Layout';
import Auth from './pages/Auth';
import Overview from './pages/Overview';
import Inventory from './pages/Inventory';
import Forecasts from './pages/Forecasts';
import Customers from './pages/Customers';
import Campaigns from './pages/Campaigns';
import WhatsAppMessages from './pages/WhatsAppMessages';
import Settings from './pages/Settings';
import './index.css';
import './App.css';
import type { DemoUser } from './utils';
import { supabase } from './lib/supabase';
import { getCurrentBusinessProfile, logoutBusinessOwner } from './services/auth';

type SessionUser = { id: string; email: string; user_metadata?: { business_name?: string } };

export default function App() {
  const [sessionUser, setSessionUser] = useState<SessionUser | null>(null);
  const [profile, setProfile] = useState<DemoUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => (localStorage.getItem('nexaflow-theme') as 'light' | 'dark') || 'light');
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('nexaflow-theme', theme); }, [theme]);
  useEffect(() => { let mounted = true; const loadSession = async () => { const { data } = await supabase.auth.getSession(); if (!mounted) return; const current = data.session?.user as SessionUser | undefined; setSessionUser(current || null); if (current) { try { const savedProfile = await getCurrentBusinessProfile(); if (mounted) setProfile(savedProfile ? { businessName: savedProfile.business_name, email: savedProfile.email } : { businessName: current.user_metadata?.business_name || 'My Business', email: current.email }); } catch { if (mounted) setProfile({ businessName: current.user_metadata?.business_name || 'My Business', email: current.email }); } } if (mounted) setLoading(false); }; void loadSession(); const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => { const current = nextSession?.user as SessionUser | undefined; setSessionUser(current || null); if (!current) setProfile(null); }); return () => { mounted = false; listener.subscription.unsubscribe(); }; }, []);
  const handleAuthenticated = async (user?: DemoUser) => {
    if (user) setProfile(user);
    const { data } = await supabase.auth.getSession();
    const current = data.session?.user as SessionUser | undefined;
    if (current) setSessionUser(current);
  };
  const logout = async () => { await logoutBusinessOwner(); setSessionUser(null); setProfile(null); };
  const user = profile || (sessionUser ? { businessName: sessionUser.user_metadata?.business_name || 'My Business', email: sessionUser.email } : null);
  if (loading) return <div className="auth-shell"><div className="auth-card"><p>Restoring your secure NexaFlow session...</p></div></div>;
  if (!sessionUser || !user) return <Auth onAuthenticated={handleAuthenticated} />;
  return <BrowserRouter><Routes><Route path="/" element={<Layout user={user} onLogout={logout} theme={theme} setTheme={setTheme} />}><Route index element={<Overview />} /><Route path="overview" element={<Overview />} /><Route path="inventory" element={<Inventory />} /><Route path="forecasts" element={<Forecasts />} /><Route path="customers" element={<Customers />} /><Route path="campaigns" element={<Campaigns />} /><Route path="whatsapp-messages" element={<WhatsAppMessages />} /><Route path="settings" element={<Settings user={user} onLogout={logout} onProfileUpdated={setProfile} />} /></Route></Routes></BrowserRouter>;
}
