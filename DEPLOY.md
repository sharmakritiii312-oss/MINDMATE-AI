# 🚀 MindMate AI — Deploy to Render.com

Step-by-step guide to get MindMate live on the internet in ~10 minutes.

---

## Prerequisites
- A [GitHub](https://github.com) account (free)
- A [Render](https://render.com) account (free — sign up with GitHub)
- Your Groq API key from [console.groq.com](https://console.groq.com) (free)

---

## Step 1 — Push your code to GitHub

Open a terminal in your project folder and run:

```bash
# Initialise git (skip if already done)
git init
git add .
git commit -m "Initial commit — MindMate AI"

# Create a repo on github.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/mindmate-ai.git
git branch -M main
git push -u origin main
```

> ✅ Your `.env` file is already in `.gitignore` — your API key will NOT be pushed.

---

## Step 2 — Create a Web Service on Render

1. Go to **[render.com](https://render.com)** → click **"New +"** → **"Web Service"**
2. Click **"Connect a repository"** → select your `mindmate-ai` repo
3. Fill in these settings:

| Setting | Value |
|---|---|
| **Name** | `mindmate-ai` |
| **Region** | Oregon (US West) or Frankfurt (EU) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt` |
| **Start Command** | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free (or Starter $7/mo for no sleep) |

---

## Step 3 — Add Environment Variables (Secrets)

In the Render dashboard, scroll to **"Environment Variables"** and add:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | `gsk_your_actual_key_here` ← paste your real key |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` |
| `MAX_HISTORY_TURNS` | `20` |

> 💡 `PORT` is injected automatically by Render — do **not** set it manually.

> 🔐 These are stored securely in Render and never exposed in your repo.

---

## Step 4 — Add Persistent Disk (keeps your database between deploys)

1. In the Render service settings, click **"Disks"** → **"Add Disk"**
2. Set:
   - **Name**: `mindmate-data`
   - **Mount Path**: `/opt/render/project/src/data`
   - **Size**: 1 GB (free with paid plans; $0.25/GB/mo on free)

> Without this, your SQLite database resets every deploy. Skip if just testing.

---

## Step 5 — Deploy!

Click **"Create Web Service"**. Render will:
1. Clone your repo
2. Install dependencies (`pip install -r requirements.txt`) — ~2 min
3. Start the server
4. Give you a live URL like `https://mindmate-ai.onrender.com`

Watch the build logs — you should see:
```
✅ Database ready (loaded at startup)
🚀 MindMate AI server started. Frontend available immediately.
```

---

## Step 6 — Test your live deployment

Open your Render URL in a browser. You should see the MindMate dashboard!

Test the API health endpoint:
```
https://mindmate-ai.onrender.com/health
```

Should return: `{"status": "ok", "ml_ready": false, ...}`
(`ml_ready: false` is expected on free tier — Groq handles AI responses)

---

## Free Tier Behaviour

| Feature | Free Tier |
|---|---|
| AI Chat (Groq) | ✅ Full speed — Groq runs in the cloud |
| Sleep / Meal / Workout plans | ✅ Works (Groq + built-in fallback) |
| HuggingFace emotion model | ⚠️ May not load (needs ~3 GB RAM) — rule-based fallback is used |
| Sleep (idle) | 💤 Spins down after 15 min idle, ~30s cold start |
| Custom domain | ✅ Free on Render |

**For production (no sleep):** Upgrade to Starter plan ($7/mo) and add the Persistent Disk.

---

## Auto-Deploy on every git push

Every time you push to `main`, Render automatically rebuilds and deploys:
```bash
git add .
git commit -m "Update something"
git push
```

---

## Troubleshooting

**Build fails with `No module named X`**
→ Make sure the package is in `requirements.txt`

**App crashes on startup**
→ Check Render logs for the error. Most common: missing env var.
→ Verify `GROQ_API_KEY` is set in Render dashboard.

**"AI Loading…" never becomes "AI Ready"**
→ Expected on free tier (not enough RAM for HuggingFace models).
→ All AI features still work via Groq API — this is fine.

**Data lost after redeploy**
→ You need the Persistent Disk (Step 4). Without it, SQLite is stored in ephemeral storage.

---

## Your Live URLs

After deployment:
- **App**: `https://mindmate-ai.onrender.com`
- **API docs**: `https://mindmate-ai.onrender.com/docs`
- **Health**: `https://mindmate-ai.onrender.com/health`
