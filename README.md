# Little Store: Python + Streamlit + Supabase (COD)

A starter online product catalogue with image/video uploads, cart, checkout using Cash on Delivery, order lookup and admin product/order management.

## Included

- Public catalogue with search/category filter
- Cart and quantity selection
- Cart shows a thumbnail for each item and can be downloaded as a PDF (with photos, descriptions, prices and totals)
- Checkout without customer account
- Cash on Delivery only; no payment gateway
- Customer order lookup using order reference + phone
- Admin page protected by a password
- Add/edit/hide/delete products
- Upload up to 5 images/videos per product
- Uploaded photos are automatically compressed to keep quality high while saving storage/bandwidth (downscaled to 1600px max, JPEG/WEBP quality 85; animated GIFs kept as-is)
- Order dashboard and COD payment-status tracking
- Supabase PostgreSQL + Supabase Storage
- Streamlit Community Cloud deployment configuration

## Free tier notes

The app code can be hosted on Streamlit Community Cloud and use Supabase Free within their current quotas. Free limits can change. Videos use storage and bandwidth quickly; resize/compress media and check your provider's current quotas. This is not a guarantee of unlimited free hosting.

## 1. Create Supabase project

1. Open https://supabase.com and create a project.
2. Open **SQL Editor**.
3. Open `supabase_schema.sql` from this project, copy its full contents and run it.
4. Go to **Project Settings > API** (the UI wording can change).
5. Copy the project URL.
6. Copy the **service_role / secret server-side key**. This app uses it only on the Streamlit server to create orders and manage uploads. Never put this key in frontend/browser code or commit it to GitHub.
7. Keep the key private. If you accidentally publish it, rotate it immediately.

## 2. Run locally (Windows PowerShell)

Install Python 3.11 or 3.12, then from this project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`) and replace the example values:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
ADMIN_PASSWORD = "a-long-unique-password"
```

Do not commit `.streamlit/secrets.toml`. `.gitignore` excludes it.

Run:

```powershell
streamlit run app.py
```

## 3. Deploy on Streamlit Community Cloud

1. Create a **private or public GitHub repository** and upload the project files. Streamlit Community Cloud access and repository requirements may vary by account; use the repo visibility allowed by your setup.
2. Do not upload `.streamlit/secrets.toml` or any `.env` file.
3. Go to https://share.streamlit.io/ and deploy `app.py`.
4. In the deployed app's settings, open **Secrets** and add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
ADMIN_PASSWORD = "a-long-unique-password"
```

5. Save and reboot/redeploy the app.
6. Open the public app URL and test product browsing, cart, checkout and order lookup.
7. Open **Admin** and log in with `ADMIN_PASSWORD`. Add a test product and test order before sharing your website.

## 4. Important security and production notes

This is a functional starter, not a fully audited production store.

- The service-role key bypasses Supabase Row Level Security. Keep it server-side only, set it as Streamlit Secrets, never put it in GitHub or browser JavaScript, and rotate it if exposed.
- The Admin page uses a shared password as a simple starter gate. Before handling significant sales/customer data, replace this with robust authentication and authorization, rate limiting, and audit logging.
- Customer order records are accessed through server-side app code. Keep the app and its secrets restricted; the customer lookup requires both order reference and phone but is not a substitute for a hardened customer portal.
- Public product media is visible to anyone who has the URL. Upload only media intended to be public.
- Test the entire order workflow and keep regular backups.
- This starter does not integrate courier tracking, email/SMS notifications, stock management, returns, tax invoices, or online payments.
- Confirm delivery areas, shipping fees, COD availability and cancellation rules before launch.
- For a real business, publish clear contact details, privacy policy, terms, shipping/return policy, and comply with applicable Indian consumer, tax and privacy requirements.
