import { supabase } from '../lib/supabase';
import { api } from '../utils';

export type BusinessProfile = {
  id: string;
  email: string;
  business_name: string;
  created_at: string;
  updated_at: string;
};

export async function createBusinessAccount({ businessName, email, password }: { businessName: string; email: string; password: string }) {
  const cleanBusinessName = businessName.trim();
  const cleanEmail = email.trim().toLowerCase();
  if (cleanBusinessName.length < 2) throw new Error('Business name must contain at least 2 characters.');
  if (password.length < 8) throw new Error('Password must contain at least 8 characters.');
  return api.post('/auth/request-signup-otp', { business_name: cleanBusinessName, email: cleanEmail, password });
}

export async function verifySignupOtp(email: string, token: string, password: string) {
  return api.post('/auth/verify-signup-otp', { email: email.trim().toLowerCase(), otp: token.trim(), password });
}

export async function loginBusinessOwner({ email, password }: { email: string; password: string }) {
  const { data, error } = await supabase.auth.signInWithPassword({ email: email.trim().toLowerCase(), password });
  if (error) throw error;
  return data;
}

export async function logoutBusinessOwner() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

export async function getCurrentBusinessProfile() {
  const { data: userData, error: userError } = await supabase.auth.getUser();
  if (userError) throw userError;
  if (!userData.user) return null;
  const { data, error } = await supabase.from('business_profiles').select('*').eq('id', userData.user.id).single();
  if (error) throw error;
  return data as BusinessProfile;
}

export async function updateBusinessProfile({ businessName, email }: { businessName: string; email: string }) {
  const cleanBusinessName = businessName.trim();
  const cleanEmail = email.trim().toLowerCase();
  const { data: userData, error: userError } = await supabase.auth.getUser();
  if (userError) throw userError;
  if (!userData.user) throw new Error('You are not logged in.');
  if (cleanBusinessName.length < 2) throw new Error('Business name must contain at least 2 characters.');

  const { error: metadataError } = await supabase.auth.updateUser({ data: { business_name: cleanBusinessName } });
  if (metadataError) throw metadataError;

  if (cleanEmail !== (userData.user.email || '').toLowerCase()) {
    const { error: emailError } = await supabase.auth.updateUser({ email: cleanEmail });
    if (emailError) throw emailError;
  }

  const { data, error } = await supabase.from('business_profiles').update({ business_name: cleanBusinessName, email: cleanEmail }).eq('id', userData.user.id).select().single();
  if (error) throw error;
  return data as BusinessProfile;
}

export async function requestPasswordReset(email: string) {
  const { error } = await supabase.auth.resetPasswordForEmail(email.trim().toLowerCase(), { redirectTo: `${window.location.origin}/reset-password` });
  if (error) throw error;
}
