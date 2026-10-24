import { useState } from 'react';
import { ArrowRight, Check, Eye, EyeOff, LockKeyhole, Mail, Sparkles } from 'lucide-react';
import type { DemoUser } from '../utils';
import { createBusinessAccount, loginBusinessOwner, verifySignupOtp } from '../services/auth';

type AuthProps = { onAuthenticated: (user?: DemoUser) => void };

export default function Auth({ onAuthenticated }: AuthProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState({ businessName: '', email: '', otp: '', password: '' });
  const update = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setNotice(''); setLoading(true);
    try {
      if (mode === 'signup') {
        if (!otpSent) {
          const data = await createBusinessAccount({ businessName: form.businessName, email: form.email, password: form.password });
          if (data.session) onAuthenticated({ businessName: form.businessName.trim(), email: form.email.trim().toLowerCase() });
          else { setOtpSent(true); setNotice('Verification code sent. Check your email and enter it below.'); }
        } else {
          await verifySignupOtp(form.email, form.otp, form.password);
          const data = await loginBusinessOwner({ email: form.email, password: form.password });
          onAuthenticated({ businessName: form.businessName.trim(), email: data.user.email || form.email.trim().toLowerCase() });
        }
      } else {
        const data = await loginBusinessOwner({ email: form.email, password: form.password });
        onAuthenticated({ businessName: data.user.user_metadata?.business_name || 'My Business', email: data.user.email || form.email.trim().toLowerCase() });
      }
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Something went wrong. Please try again.'); }
    finally { setLoading(false); }
  };

  return <div className="auth-shell"><div className="auth-brand"><div className="brand-mark">N</div><span>NexaFlow</span></div><div className="auth-grid"><section className="auth-intro"><div className="eyebrow"><Sparkles size={15} /> RETAIL OPERATIONS, REFINED</div><h1>Turn every restock into a reason to reconnect.</h1><p>One calm workspace for inventory intelligence, customer engagement, and revenue momentum.</p><div className="auth-proof"><div className="proof-icon"><Check size={18} /></div><div><strong>Built for business owners</strong><span>Live inventory signals and campaigns in one place.</span></div></div></section><section className="auth-card"><div className="auth-card-head"><span className="auth-kicker">{mode === 'login' ? 'WELCOME BACK' : 'START YOUR WORKSPACE'}</span><h2>{mode === 'login' ? 'Sign in to NexaFlow' : 'Create your account'}</h2><p>{mode === 'login' ? 'Use your registered business email and password.' : otpSent ? 'Enter the verification code sent to your email.' : 'Create your business workspace securely.'}</p></div><form onSubmit={submit} className="auth-form">{mode === 'signup' && <label>Business name<input value={form.businessName} onChange={(e) => update('businessName', e.target.value)} placeholder="Keystone Market" required disabled={otpSent} /></label>}<label>Email address<div className="input-icon"><Mail size={17} /><input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} placeholder="you@business.com" required disabled={otpSent} /></div></label>{mode === 'signup' && otpSent && <label>Verification code<input value={form.otp} onChange={(e) => update('otp', e.target.value)} placeholder="Enter the code from your email" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required /></label>}<label>Password<div className="input-icon"><LockKeyhole size={17} /><input type={showPassword ? 'text' : 'password'} value={form.password} onChange={(e) => update('password', e.target.value)} placeholder="At least 8 characters" minLength={8} required disabled={otpSent} /><button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>{notice && <div className="auth-notice">{notice}</div>}<button className="primary-button auth-submit" type="submit" disabled={loading}>{loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : otpSent ? 'Verify email' : 'Create account'}<ArrowRight size={17} /></button></form><button className="auth-switch" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setOtpSent(false); setNotice(''); }}>{mode === 'login' ? 'New here? Create a business account' : 'Already have an account? Sign in'}</button><small className="auth-footnote">NexaFlow sends signup verification codes through the secure backend and Brevo HTTPS API. Supabase manages passwords and sessions.</small></section></div></div>;
}
