# NexaFlow data and OTP setup

## 1. Seed the dashboard database

The dashboard seed data is stored in the local SQLite database at `backend/nexaflow.db`. The source of truth is `backend/seed.py`. It creates 29 products from the `CATEGORIES` dictionary, 1,500 customers from the Indian name lists, 12 months of order history, six settings, two demo campaigns, and 12 demo WhatsApp messages.

On Windows PowerShell:

```powershell
cd Nexaflow\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python main.py
```

On Windows Command Prompt:

```bat
cd Nexaflow\backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
python seed.py
python main.py
```

On macOS/Linux:

```bash
cd Nexaflow/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py
python main.py
```

`python seed.py` clears and recreates the demo tables. Run it when you want to reset the data. Do not run it on a production database because it deletes existing demo records before reseeding.

Keep the backend terminal running at `http://localhost:8000`. The frontend calls the backend through `VITE_API_BASE_URL=http://localhost:8000/api`. With the backend running, Overview, Inventory, Forecasts, Customers, Campaigns, and WhatsApp Messages display the real SQLite seed results. If the backend is temporarily unavailable, the frontend uses a small matching fallback dataset so every page still renders.

Start the frontend in a second terminal:

```bash
cd Nexaflow/frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 2. Supabase profile database

Run the previously provided `business_profiles` SQL in Supabase SQL Editor. It must include the foreign key to `auth.users`, RLS policies, the `handle_new_user` trigger, and the email-sync trigger. Passwords are not stored in `business_profiles`; Supabase Auth stores them securely.

Fill `frontend/.env`:

```env
VITE_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY
VITE_API_BASE_URL=http://localhost:8000/api
```

Only use the Supabase `anon public` key in the frontend. Never put a Supabase service-role key or Brevo API key in a `VITE_*` variable.

## 3. Configure OTP email delivery with Brevo

In Supabase Dashboard:

1. Open **Project Settings → Authentication → SMTP Settings**.
2. Enable custom SMTP.
3. Use Brevo SMTP, normally `smtp-relay.brevo.com` on port `587` with TLS.
4. Use the Brevo SMTP login and SMTP key/password supplied by Brevo.
5. Use a sender email that is verified in Brevo.
6. Save the SMTP settings.
7. Open **Authentication → Providers → Email** and enable email confirmation.
8. Open **Authentication → Email Templates → Confirm signup** and make sure the template includes `{{ .Token }}` if you want users to enter the numeric OTP in NexaFlow. Keep the confirmation URL variables if you also want link confirmation.

The NexaFlow signup flow calls `supabase.auth.signUp`. Supabase sends the confirmation email through the configured Brevo SMTP connection. The user enters the received code in the NexaFlow verification field, and the frontend calls `supabase.auth.verifyOtp({ email, token, type: 'signup' })`. After verification, the trigger creates the user's `business_profiles` row.

For an existing user, the app calls `supabase.auth.signInWithPassword`. Logout calls `supabase.auth.signOut`. A changed email is sent through the same Supabase/Brevo confirmation pipeline.

## 4. Verify everything

After creating an account:

1. Check **Supabase → Authentication → Users** for the user.
2. Check **Supabase → Table Editor → business_profiles** for the business name and email.
3. Check the Brevo logs to confirm delivery.
4. Sign out and sign back in with the same email/password.
5. Check the dashboard pages while the backend is running; they should show data from `seed.py`.

Sample data and a snapshot from the seeded SQLite database are in `sample-data/`. The snapshot currently contains 29 products, 1,500 customers, 3,478 orders, 6,093 order items, 6 settings, 2 campaigns, and 12 messages.
