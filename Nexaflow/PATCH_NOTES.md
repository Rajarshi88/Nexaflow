# NexaFlow update

The frontend uses Supabase Auth instead of localStorage for business-owner authentication. Supabase stores passwords, sessions, email confirmation, and logout state. The `business_profiles` table stores the authenticated user id, email, and business name through the SQL trigger and row-level security policies.

The signup flow calls `supabase.auth.signUp`, displays the email verification-code step when confirmation is required, and verifies the code with `supabase.auth.verifyOtp`. Login uses `signInWithPassword`. Logout uses `signOut`. The app restores existing sessions on startup with `getSession` and listens for auth changes.

The profile settings screen updates business name and email through Supabase. A changed email triggers Supabase's email confirmation flow.

## Seeded pages and search

Every dashboard page now renders useful seed content when the API is unavailable. Overview has seeded KPIs, charts, alerts, and campaign activity. Inventory has five seeded products. Customers has five seeded customers. Campaigns has two seeded campaigns. WhatsApp Messages has seeded conversations. Forecasts has seeded product forecast charts and detail data. Settings renders its preference controls without waiting for an API response.

Page-level search is functional on Inventory, Customers, Campaigns, and WhatsApp Messages. Inventory also includes clear and SKU sort controls. The workspace name/selector pill was removed from the top of the left sidebar; the profile menu remains at the bottom of the sidebar and in the top navigation.

The `sample-data` folder includes `inventory_sample.csv`, `customers_sample.csv`, `campaigns_sample.csv`, and a README. Upload `inventory_sample.csv` through Inventory → Connect inventory to test the file-selection flow.

## Environment

Fill these values in `frontend/.env`:

```env
VITE_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
VITE_API_BASE_URL=http://localhost:8000/api
```

Do not place the Brevo API key in the frontend. Brevo should be configured as the SMTP/email provider for Supabase Authentication, or called from a secure backend only. Never expose a Brevo secret in a `VITE_*` variable.

## Run

```bash
cd frontend
npm install
npm run dev
```

The production build was verified with `npm run build`.
