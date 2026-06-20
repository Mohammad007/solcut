# SlotCut — Backend (Flask + SQLite)

The single Flask server provides:

| Surface | Path | Consumer |
|---|---|---|
| REST API | `/api/v1/...` | Flutter customer & provider apps |
| Admin panel | `/admin/...` | Browser (session login) |
| Public website | `/`, `/shop/<id>` | SEO pages |
| Uploaded images | `/uploads/...` | served as static files |
| App download | `/download/app` | serves `downloads/SlotCut.apk` |

**Tech:** Flask + Flask-SocketIO + SQLAlchemy (SQLite) + JWT auth. One process
serves the API, the Jinja admin panel, the marketing website and WebSockets.

## Quick start (Windows / PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # defaults run everything in MOCK mode

# Create tables + demo data (3 Indore providers + a test customer)
python -m app.seed

# Run (API + admin + website + websockets on port 5000)
python run.py
```

Then open:
- http://localhost:5000/ — landing page
- http://localhost:5000/admin — admin panel (login `admin` / `slotcut@admin123`)
- http://localhost:5000/api/v1/health — API health check

## Dev mode behaviour (no external accounts needed)

| Integration | Mock behaviour |
|---|---|
| OTP | code is always **`123456`** (also returned as `dev_otp` and printed to console) |
| Payments (Razorpay) | orders auto-succeed; mock order ids verify locally |
| FCM push | logged to console only |

Switch any of these to real providers by filling the matching keys in `.env`
(`OTP_PROVIDER=twilio`/`msg91`, `RAZORPAY_KEY_*`, `FIREBASE_CREDENTIALS_PATH`).

## Auth flow (customer or provider)

```
POST /api/v1/auth/send-otp     { "phone": "9876543210", "user_type": "customer" }
POST /api/v1/auth/verify-otp   { "phone": "9876543210", "otp": "123456", "user_type": "customer" }
   -> { access_token, refresh_token, user, is_new_user }
```

Send the access token as `Authorization: Bearer <token>` on protected routes.
JWTs carry a `role` claim (`customer` | `provider`) enforced by the route decorators.

## Try it (after seeding)

```bash
# Nearby providers around Indore
curl "http://localhost:5000/api/v1/providers/nearby?lat=22.75&lng=75.89&radius=10"

# Login as the demo customer
curl -X POST http://localhost:5000/api/v1/auth/send-otp \
  -H "Content-Type: application/json" -d '{"phone":"9876543210","user_type":"customer"}'
curl -X POST http://localhost:5000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" -d '{"phone":"9876543210","otp":"123456","user_type":"customer"}'
```

## Migrations (optional, for schema changes over time)

`run.py` / `flask init-db` use `db.create_all()` for a fast start. For versioned
schema changes use Flask-Migrate:

```powershell
flask --app run.py db init        # once
flask --app run.py db migrate -m "message"
flask --app run.py db upgrade
```

## Deploy to Railway

Deployment files live in this folder: [`railway.json`](railway.json),
[`Procfile`](Procfile), [`runtime.txt`](runtime.txt) and the gunicorn
entrypoint [`wsgi.py`](wsgi.py).

In production the app runs under **gunicorn + an eventlet worker** (real WebSocket
support) on **Python 3.11** — eventlet isn't reliable on 3.13, so `runtime.txt`
pins 3.11 for the deploy while local dev stays on 3.13 with `threading`.

```
gunicorn --worker-class eventlet -w 1 wsgi:app --bind 0.0.0.0:$PORT
```

### Steps

1. **Push the repo to GitHub.**
2. On [railway.app](https://railway.app): **New Project → Deploy from GitHub repo**.
   If the repo root isn't `backend/`, set the service **Root Directory** to `backend`.
   Railway auto-detects Nixpacks; `railway.json` supplies the start command + health check.
3. **Add a Volume** (Service → Variables → Volumes) mounted at **`/data`** so the
   SQLite DB, uploaded images and the APK survive redeploys (the container FS is
   otherwise ephemeral).
4. **Set environment variables** (Service → Variables):

   | Variable | Value | Why |
   |---|---|---|
   | `SOCKETIO_ASYNC_MODE` | `eventlet` | match the gunicorn worker |
   | `SECRET_KEY` / `JWT_SECRET_KEY` | long random strings | security |
   | `ADMIN_USERNAME` / `ADMIN_PASSWORD` | your choice | admin login |
   | `BASE_URL` | `https://<your>.up.railway.app` | absolute image URLs |
   | `DATABASE_URL` | `sqlite:////data/slotcut.db` | DB on the volume (note 4 slashes) |
   | `UPLOAD_FOLDER` | `/data/uploads` | persist uploaded images |
   | `DOWNLOAD_FOLDER` | `/data/downloads` | persist the APK |
   | `SEED_ON_BOOT` | `1` (first deploy only) | seed demo data, then remove |

   Mock integrations stay on until you add the real keys
   (`OTP_PROVIDER`, `RAZORPAY_KEY_*`, `FIREBASE_CREDENTIALS_PATH`).
5. **Deploy.** Railway builds, then hits `/api/v1/health` to confirm it's live.
6. Point the Flutter app at the Railway URL via
   `--dart-define=API_BASE=https://<your>.up.railway.app`.

`PORT` is provided by Railway automatically — don't hard-code it. The schema is
created on boot by `wsgi.py` (idempotent `create_all`).

> **Scaling note:** WebSockets + the eventlet worker require **one** web instance
> (`-w 1`). To run multiple instances later, move to Postgres (set `DATABASE_URL`
> to the Railway Postgres URL — add `psycopg[binary]` to requirements) and add a
> Redis message queue for SocketIO.

## Notes

- **SocketIO async mode**: `threading` locally (Python 3.13 friendly, no extra deps),
  `eventlet` in production (see Railway section). Controlled by `SOCKETIO_ASYNC_MODE`.
- SQLite DB lives at `backend/instance/slotcut.db` locally, or on the mounted volume
  via `DATABASE_URL` in production.
- Image URLs: the backend stores absolute URLs built from `BASE_URL`. The Flutter
  app also normalises any `/uploads/...` URL onto its configured API host, so a
  mismatch (e.g. tunnel/localhost) still resolves.
- Real-time queue events are emitted to room `provider_<id>`:
  `queue:updated`, `token:called`, `shop:status`.
