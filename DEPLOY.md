# Deploy PLPG for free (Vercel + Render + MongoDB Atlas)

Your **local setup stays the same**: `python app.py` + `npm run dev`.  
Production uses separate env vars on Vercel and Render — not your local `.env`.

## Architecture

| Part | Host | Cost |
|------|------|------|
| Frontend (`my-react-app`) | Vercel | Free |
| Backend (`backend-python`) | Render | Free (sleeps when idle) |
| Database | MongoDB Atlas M0 | Free |

OpenAI API usage is **not free** (quizzes, remediation, chat).

---

## 1. MongoDB Atlas

1. Create account at https://www.mongodb.com/cloud/atlas
2. Create **M0 FREE** cluster
3. **Database Access** → user + password
4. **Network Access** → Allow `0.0.0.0/0`
5. Copy connection string:
   ```
   mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/plpg?retryWrites=true&w=majority
   ```

---

## 2. Push code to GitHub

```bash
git add .
git commit -m "Add Vercel and Render deployment config"
git push origin main
```

Never commit `.env` files (already in `.gitignore`).

---

## 3. Deploy backend on Render (free)

### Option A — Blueprint (uses `render.yaml` in repo root)

1. https://dashboard.render.com → **Blueprints** → **New Blueprint Instance**
2. Connect GitHub repo
3. After create, open **plpg-api** → **Environment** and add:

| Variable | Value |
|----------|--------|
| `SECRET_KEY` | random 40+ chars |
| `MONGODB_URI` | Atlas connection string |
| `JWT_SECRET` | random 40+ chars |
| `JWT_REFRESH_SECRET` | random 40+ chars |
| `ADMIN_JWT_SECRET` | random 40+ chars |
| `ADMIN_JWT_REFRESH_SECRET` | random 40+ chars |
| `OPENAI_API_KEY` | your OpenAI key |
| `QUIZ_PASSING_SCORE` | `70` |

4. Deploy → copy URL: `https://plpg-api.onrender.com` (yours may differ)
5. Test: `https://YOUR-SERVICE.onrender.com/api/health`

### Option B — Manual Web Service

- Root directory: `backend-python`
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`
- Plan: **Free**

### Seed catalog (once)

On your PC with Atlas URI in `backend-python/.env`:

```bash
cd backend-python
python seed_recommendation_catalog.py
```

---

## 4. Deploy frontend on Vercel (free)

1. https://vercel.com → **Add New** → **Project** → import GitHub repo
2. Settings:
   - **Root Directory**: `my-react-app`
   - **Framework**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. **Environment Variables** (required):

   | Name | Value |
   |------|--------|
   | `VITE_API_BASE_URL` | `https://YOUR-SERVICE.onrender.com/api` |

4. Deploy → copy URL: `https://your-app.vercel.app`

---

## 5. Connect frontend ↔ backend (CORS)

On Render → **plpg-api** → **Environment**, add:

```
FRONTEND_BASE_URL=https://your-app.vercel.app
```

Redeploy backend. Without this, the browser blocks API calls from Vercel.

---

## 6. Verify

1. Open Render API health URL (wake cold server — first load may take ~30s)
2. Open Vercel app → login → quiz → remediation
3. Change default admin password after first login

---

## Local development (unchanged)

```bash
# Backend
cd backend-python
python app.py

# Frontend
cd my-react-app
npm run dev
```

No `VITE_API_BASE_URL` needed locally — Vite proxies `/api` to port 5000.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on Vercel | Set `VITE_API_BASE_URL` before build |
| CORS error | Set `FRONTEND_BASE_URL` on Render to exact Vercel URL |
| 404 on `/dashboard` | `my-react-app/vercel.json` rewrites (already in repo) |
| Slow first request | Render free tier slept — wait or hit `/api/health` first |
| Remediation timeout | Retry after API is warm; free tier + OpenAI can be slow |
