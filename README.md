# LearnFlow - Smart Spaced Repetition Learning Platform

A student-friendly web application that uses spaced repetition (intervals: Day 1, 3, 6, 29, 179) to help you remember what you learn. Upload PDFs, paste text, add links — AI auto-generates titles & descriptions, and you get automatic review reminders.

## Live Demo
- **Demo URL**: https://3000-immqsa4sptqvxeioeqz59-02b9cc79.sandbox.novita.ai
- **Demo Login**: `username: demo` / `password: demo123`

---

## File Structure

```
webapp/
├── backend/                    # Flask Backend (deploy to Render)
│   ├── app.py                  # Full production backend with Supabase + Google APIs
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variables template
│
├── frontend/                   # React Frontend (deploy to Vercel)
│   ├── src/
│   │   ├── main.jsx            # React entry point
│   │   ├── App.jsx             # Router + AuthProvider
│   │   ├── hooks/
│   │   │   └── useAuth.jsx     # Authentication context & hooks
│   │   ├── utils/
│   │   │   └── api.jsx         # Axios API client (all API calls)
│   │   ├── components/
│   │   │   ├── Navbar.jsx      # Responsive navigation bar
│   │   │   ├── RevisionCard.jsx # Task/revision card component
│   │   │   ├── StatsCard.jsx   # Dashboard statistics card
│   │   │   ├── EmptyState.jsx  # Empty state placeholder
│   │   │   └── LoadingScreen.jsx # Loading animation
│   │   ├── pages/
│   │   │   ├── Login.jsx       # Login page (email + Google)
│   │   │   ├── Register.jsx    # Registration page
│   │   │   ├── Dashboard.jsx   # Main dashboard with stats
│   │   │   ├── Upload.jsx      # Upload file/URL/text + AI preview
│   │   │   ├── TodayTasks.jsx  # Today's tasks + overdue + completed
│   │   │   ├── Upcoming.jsx    # Upcoming reviews grouped by date
│   │   │   └── History.jsx     # Learning history
│   │   └── styles/
│   │       └── index.css       # Tailwind CSS + custom styles
│   │
│   ├── index.html              # HTML template
│   ├── package.json            # Node dependencies
│   ├── vite.config.js          # Vite configuration with API proxy
│   ├── tailwind.config.js      # Tailwind theme + animations
│   └── postcss.config.js       # PostCSS config
│
├── serve.py                    # Demo server (combined Flask + static serving)
├── ecosystem.config.cjs        # PM2 configuration for demo
└── README.md                   # This file
```

---

## Features

### Completed
- User registration & login (username/password)
- Google OAuth sign-in
- Google Drive connection (auto-upload files to Drive)
- File upload (PDF, DOC, DOCX, TXT, MD)
- URL content extraction
- Text/notes paste
- AI-powered title & description generation (Gemini API)
- Preview & edit before saving
- Spaced repetition scheduling (Day 1, 3, 6, 29, 179)
- Today's tasks dashboard with overdue tracking
- Mark complete / Postpone / Skip actions
- Upcoming tasks grouped by date
- Learning history
- Streak tracking
- Responsive design (mobile, tablet, desktop)
- Smooth animations (Framer Motion)
- Glass morphism UI with gradient accents

### Spaced Repetition Mechanism
When you skip a task:
- It moves to the **next day** (not lost)
- If you complete it later, the streak continues
- Overdue tasks show separately with a red indicator
- You can postpone to tomorrow or skip (pushes by 1 day)

---

## Setup Guide

### 1. Supabase Setup

Go to [supabase.com](https://supabase.com), create a project, then run this SQL in the **SQL Editor**:

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User state (Drive connection, streak, etc.)
CREATE TABLE IF NOT EXISTS user_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  drive_connected BOOLEAN DEFAULT FALSE,
  spreadsheet_id TEXT,
  current_streak INTEGER DEFAULT 0,
  last_completion_date TEXT,
  google_drive_credentials JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Learning items
CREATE TABLE IF NOT EXISTS learnings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content TEXT,
  source_type TEXT,
  source_name TEXT,
  supabase_path TEXT,
  drive_link TEXT,
  completed BOOLEAN DEFAULT FALSE,
  revision_stage INTEGER DEFAULT 0,
  revision_count INTEGER DEFAULT 0,
  next_revision_date TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Revisions (spaced repetition schedule)
CREATE TABLE IF NOT EXISTS revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  learning_id UUID REFERENCES learnings(id) ON DELETE CASCADE,
  heading TEXT NOT NULL,
  description TEXT,
  drive_link TEXT,
  url TEXT,
  supabase_path TEXT,
  stage INTEGER DEFAULT 1,
  scheduled_date TEXT NOT NULL,
  completed BOOLEAN DEFAULT FALSE,
  completed_date TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Uploaded files tracking (for cleanup)
CREATE TABLE IF NOT EXISTS uploaded_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  filename TEXT NOT NULL,
  supabase_path TEXT NOT NULL,
  upload_date TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_revisions_user_date ON revisions(user_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_revisions_user_completed ON revisions(user_id, completed);
CREATE INDEX IF NOT EXISTS idx_learnings_user ON learnings(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Add SMS reminder settings to user_state
alter table if exists public.user_state
  add column if not exists notification_phone text,
  add column if not exists sms_notifications_enabled boolean not null default false,
  add column if not exists notification_timezone text not null default 'UTC',
  add column if not exists notification_hour integer not null default 8,
  add column if not exists last_sms_sent_date date;

```

Then in **Supabase Settings**:
- Copy your **Project URL** (e.g., `https://xxxxx.supabase.co`)
- Copy your **anon/public key** from API settings

### 2. Google Cloud Setup (for OAuth + Drive)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable these APIs:
   - Google Drive API
   - Google Sheets API
   - Google People API (for OAuth)
4. Go to **Credentials** > **Create Credentials** > **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Add Authorized redirect URIs:
   ```
   http://localhost:5000/api/auth/google/callback
   http://localhost:5000/api/drive/callback
   https://YOUR-RENDER-URL.onrender.com/api/auth/google/callback
   https://YOUR-RENDER-URL.onrender.com/api/drive/callback
   ```
7. Copy your **Client ID** and **Client Secret**

### 3. Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create a new API key
3. Copy the key

---

## Local Development

### Option A: Demo Mode (no external services needed)
```bash
# From the project root
cd webapp

# Install frontend deps and build
cd frontend && npm install && npm run build && cd ..

# Install demo server deps
pip install flask flask-cors python-dotenv werkzeug

# Run demo server
python serve.py

# Visit http://localhost:3000
# Login with: demo / demo123
```

### Option B: Full Mode (with Supabase, Google, Gemini)

**Terminal 1 — Backend:**
```bash
cd webapp/backend

# Create .env from template
cp .env.example .env
# Edit .env with your real credentials

# Install Python dependencies
pip install -r requirements.txt

# Run backend
python app.py
# Backend runs at http://localhost:5000
```

**Terminal 2 — Frontend:**
```bash
cd webapp/frontend

# Install dependencies
npm install

# Run dev server (auto-proxies /api to localhost:5000)
npm run dev
# Frontend runs at http://localhost:5173
```

---

## Hosting

### Deploy Backend to Render

1. **Create a Git repo** (or push to GitHub)
   ```bash
   cd webapp/backend
   git init
   git add .
   git commit -m "Initial backend"
   # Push to GitHub
   ```

2. **Go to [render.com](https://render.com)** > New > Web Service

3. **Settings:**
   - **Root Directory**: `backend` (if monorepo) or `/` (if separate repo)
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`

4. **Environment Variables** (add in Render dashboard):
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_BUCKET=learning-intake-uploads
   GOOGLE_OAUTH_CLIENT_ID=your-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   GEMINI_API_KEY=your-gemini-key
   FLASK_SECRET_KEY=generate-a-strong-random-string
   BACKEND_URL=https://your-app.onrender.com
   FRONTEND_URL=https://your-app.vercel.app
   ```

5. **Deploy!** Render auto-builds and deploys.

### Deploy Frontend to Vercel

1. **Push frontend to GitHub:**
   ```bash
   cd webapp/frontend
   git init
   git add .
   git commit -m "Initial frontend"
   # Push to GitHub
   ```

2. **Go to [vercel.com](https://vercel.com)** > New Project > Import from GitHub

3. **Settings:**
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

4. **Environment Variables** (add in Vercel dashboard):
   ```
   VITE_API_URL=https://your-app.onrender.com
   ```

5. **Deploy!**

### After Deployment

Update Google OAuth redirect URIs in Google Cloud Console:
```
https://your-app.onrender.com/api/auth/google/callback
https://your-app.onrender.com/api/drive/callback
```

Update Render env vars:
```
BACKEND_URL=https://your-app.onrender.com
FRONTEND_URL=https://your-app.vercel.app
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login with username/password |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/auth/google` | Get Google OAuth URL |
| GET | `/api/drive/connect` | Connect Google Drive |
| POST | `/api/drive/disconnect` | Disconnect Drive |
| POST | `/api/upload/preview` | Generate AI preview (multipart) |
| POST | `/api/upload/save` | Save learning item |
| GET | `/api/revisions/today` | Today's tasks |
| GET | `/api/revisions/overdue` | Overdue tasks |
| GET | `/api/revisions/completed` | Completed today |
| GET | `/api/revisions/upcoming` | Upcoming reviews |
| GET | `/api/revisions/stats` | Dashboard statistics |
| POST | `/api/revisions/:id/complete` | Mark task complete |
| POST | `/api/revisions/:id/postpone` | Postpone to tomorrow |
| POST | `/api/revisions/:id/skip` | Skip (move +1 day) |
| GET | `/api/learnings` | Learning history |
| GET | `/api/health` | Health check |

---

## Tech Stack
- **Frontend**: React 18 + Vite + Tailwind CSS + Framer Motion
- **Backend**: Flask + Gunicorn (Python)
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage (file uploads)
- **Auth**: Custom + Google OAuth 2.0
- **AI**: Google Gemini 2.5 Flash
- **Cloud**: Google Drive + Sheets integration
- **Hosting**: Render (backend) + Vercel (frontend)
