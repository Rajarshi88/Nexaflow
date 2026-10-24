# Backend OTP + Brevo API setup

NexaFlow signup no longer depends on Supabase SMTP. The browser calls FastAPI, FastAPI generates a six-digit code, stores only a hash in SQLite, sends the code through Brevo's HTTPS API, verifies the code, and creates the confirmed Supabase Auth user with the server-only service-role key.

## 1. Create backend/.env

From Git Bash:

```bash
cd /c/Users/YOUR_USERNAME/Desktop/nexaflow2/backend
cp .env.example .env
nano .env
```

Fill the values:

```env
BREVO_API_KEY=your_brevo_http_api_key
BREVO_SENDER_EMAIL=your_verified_sender@gmail.com
BREVO_SENDER_NAME=NexaFlow

SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_server_only_service_role_key

OTP_HASH_SECRET=use_a_long_random_string_here
OTP_EXPIRY_MINUTES=10
OTP_RESEND_SECONDS=60
```

`BREVO_API_KEY` is the Brevo HTTP API key from **Settings → SMTP & API → API Keys**. This is intentionally different from the SMTP key. `SUPABASE_SERVICE_ROLE_KEY` is the server-only key from **Project Settings → API**. Never place either value in `frontend/.env`, a React component, or a Git repository.

Use a Brevo-verified sender in `BREVO_SENDER_EMAIL`. A personal Gmail address can be used for testing if that exact address is verified as a Brevo sender.

## 2. Install and start the backend

```bash
cd /c/Users/YOUR_USERNAME/Desktop/nexaflow2/backend
source ../.venv/Scripts/activate
python -m pip install -r requirements.txt
python main.py
```

On startup, FastAPI calls `init_db()` and creates the `signup_otps` table in the existing `nexaflow.db` if it does not already exist. You do not need to run a separate OTP SQL query for the local SQLite setup.

## 3. Signup flow

The frontend calls:

```text
POST /api/auth/request-signup-otp
POST /api/auth/verify-signup-otp
```

The first endpoint generates and sends the OTP. It stores only the HMAC hash, email, business name, expiry, attempt count, and timestamps. The password is not stored by the OTP table. The second endpoint receives the password over the local HTTPS/HTTP development connection, verifies the code, and calls the Supabase Admin Auth REST endpoint from the backend. Supabase stores the password securely and marks the email confirmed.

After verification, the frontend signs in with `supabase.auth.signInWithPassword`, so the normal Supabase session is created in the browser.

## 4. Supabase settings

Supabase SMTP is no longer required for signup OTP delivery. Keep Email authentication enabled in **Authentication → Providers → Email**, but disable **Confirm email** if you want to avoid Supabase sending its own confirmation email. The backend creates users with `email_confirm: true` only after the Brevo OTP has been verified.

Keep the existing `business_profiles` table and `handle_new_user` trigger. The trigger receives the business name from `user_metadata.business_name` when the backend creates the user.

The frontend still needs only the public values in `frontend/.env`:

```env
VITE_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_ANON_OR_PUBLISHABLE_PUBLIC_KEY
VITE_API_BASE_URL=http://localhost:8000/api
```

Never use the Supabase service-role key as `VITE_SUPABASE_ANON_KEY`.

## 5. Run the frontend on port 5174

Open a second Git Bash window:

```bash
cd /c/Users/YOUR_USERNAME/Desktop/nexaflow2/frontend
npm install
npm run dev -- --port 5174
```

Open:

```text
http://localhost:5174
```

## 6. Test the API before testing the UI

With the backend running, this should return JSON:

```bash
curl http://localhost:8000/api/overview
```

To request an OTP directly:

```bash
curl -X POST http://localhost:8000/api/auth/request-signup-otp \
  -H 'Content-Type: application/json' \
  -d '{"business_name":"Test Store","email":"your@gmail.com","password":"TestPassword123"}'
```

Do not use a real production password in a shell command because shell history can retain it. This curl command is only a local diagnostic.

If Brevo fails, FastAPI returns the Brevo API response in the browser notice and the terminal logs. This is now independent of SMTP port restrictions.
