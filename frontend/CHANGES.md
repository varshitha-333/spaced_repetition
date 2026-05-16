# LearnFlow — Redesign & Premium Launch Package

Everything in this drop is **additive or drop-in replacement**. Your existing
`app.py`, Supabase, and Google Drive flow are preserved.

---

## ⚡ TL;DR — what to do

1. Copy `backend/premium_routes.py` + `backend/twilio_helper.py` next to your `app.py`.
2. Add **3 lines** to `app.py` (see `backend/app_patch.md`).
3. Run the **SQL block** in `backend/app_patch.md` once in Supabase.
4. Replace these frontend files (paths shown in repo root):
   - `frontend/tailwind.config.js`
   - `frontend/src/index.css`
   - `frontend/src/main.jsx`
   - `frontend/src/App.jsx`
   - `frontend/src/hooks/useAuth.jsx`
   - `frontend/src/services/api.jsx` *(NEW location — replaces `services/api.jsx`)*
   - All files inside `frontend/src/pages/`
   - All files inside `frontend/src/components/`
5. `cd frontend && npm install` (no new deps required — uses `framer-motion`, `react-hot-toast`, `react-router-dom` already in your `package.json`).
6. `npm run dev` and head to `/` for the new landing page.

> **Note on api import path:** the old `services/api.jsx` is now at `services/api.jsx`.
> Either move the file or update imports — the new pages all use `../services/api`.

---

## ✨ What changed

### 1. Landing page (`/`)
- New **business-style** landing page with animated hero, feature grid, 4-step "how it works", Premium ribbon CTA, and a **Top 5 Reviews** carousel (ranked by Gemini quality score).
- Pre-login users now see this instead of being bounced to `/login`.

### 2. Pricing page (`/pricing`)
- Matches your reference screenshot (Free ₹0 / Core ₹199 / Premium ₹499) with the "Best for most students" highlight on Core and the **"🎁 FREE for 30 days"** badge on Premium.

### 3. Dummy payment page (`/payment`)
- Student fills name + email + (optional) phone.
- Coupon field accepts: `LAUNCH30`, `STUDENT30`, `FIRST100`, `LEARNFREE` (case-insensitive).
- Valid coupon → total becomes **₹0**, backend stamps `premium_expires_at = now + 30 days`.
- Returns a receipt UI with a unique `LF-XXXXXXXX` id.
- Already-premium users see a friendly "you're already on Premium" screen.

### 4. Dashboard (`/dashboard`) — calm redesign
- **Predictable layout** every time: greeting → today's revisions → catching up → 3 quick actions → premium teaser.
- Skeleton loaders, real empty states.
- **One-button SMS enable** (modal): just type phone → enable.
- Drive status now **reads from `/api/auth/me` live** — no more stale "not connected".
- Streak coach line at the top (Gemini-generated for Premium users, falls back gracefully).
- Launch ribbon at top for non-Premium users.

### 5. Profile page (`/profile`) — NEW
Tabs: **Profile · SMS · Drive · Review**
- Edit display name, email, phone (saved to `user_state`).
- SMS toggle + phone field + "Send test SMS" button (works in real or mock mode).
- Drive connect/disconnect with live status — fixes the bug where Drive was connected but still shown as "Not connected".
- Submit reviews — Gemini scores them server-side; top 5 surface on the landing page.
- Shows live "Premium · N days left" badge.

### 6. Premium AI Lab (`/premium`) — NEW
Five tools unlocked only while `premium_expires_at` is in the future:
- 📝 **Smart Summary** — 5 memorable bullets from any pasted text.
- 🃏 **Flashcard Generator** — 6 flip cards.
- 🎯 **Quiz Me** — 5 MCQs with explanations + answer highlighting.
- 🕸️ **Concept Linker** — clusters all your saved resources into 3-6 concept groups.
- 💬 **Streak Coach** — runs silently on the dashboard, writes a one-line motivator each visit.

Non-Premium users see a locked screen with a CTA to claim free Premium.

### 7. SMS automation (Twilio) — NEW
- `/api/sms/enable` — saves phone + enabled flag, fires a confirmation SMS.
- `/api/sms/test` — one-off test SMS.
- `/api/sms/cron/morning` and `/api/sms/cron/night` — public cron endpoints
  protected by `X-Cron-Secret` header. Iterates all opted-in users.
- **Hybrid mode**: if `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_NUMBER` env vars are
  present, sends real SMS; otherwise logs to stdout (mock). No code change required.
- `backend/twilio_helper.py` — tiny local CLI to verify your Twilio creds work
  before deploying.

### 8. Reviews system — NEW
- `POST /api/reviews` — student submits rating + text.
- Server calls Gemini: *"Rate this review 0-10 for clarity, helpfulness, specificity."*
- Stores the score; `GET /api/reviews/top` returns top 5 ranked by score then rating.
- Public endpoint — used on the landing page.

### 9. Design system
- New Tailwind theme: **calm pastel** (indigo + cream + peach).
- New utility classes: `.card`, `.btn-primary`, `.pill-indigo`, `.input`, `.shimmer`.
- Subtle animations everywhere (Framer Motion) — fade-in, slide-up, float, pop.
- Body uses a soft radial mesh background for depth without noise.
- **Predictable navbar** with 5 tabs only (Today · Add · Upcoming · AI Lab · History) + profile button on the right.

### 10. UX details that students will feel
- All toasts are warm, never scolding ("Pushed to tomorrow", "Locked in 🎯").
- Empty states with a sage 🌿 instead of "you have 0 items".
- Streak shown with kind framing ("14 days strong" not "don't break it").
- Marketing copy on landing emphasises **calmness** and **predictability** — the exact promise students respond to.

---

## 🗃️ New API endpoints (all added by `premium_routes.py`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET  | `/api/premium/status` | ✅ | Returns `{is_premium, days_left, expires_at}` |
| POST | `/api/premium/redeem` | ✅ | Body `{name,email,phone,coupon}` → 30-day Premium |
| POST | `/api/sms/enable` | ✅ | Body `{phone, enabled}` |
| POST | `/api/sms/test` | ✅ | Send one-off test |
| POST | `/api/sms/cron/morning` | header `X-Cron-Secret` | Fans out morning SMS |
| POST | `/api/sms/cron/night`   | header `X-Cron-Secret` | Fans out night SMS |
| POST | `/api/reviews` | ✅ | Submit a review (Gemini-scored) |
| GET  | `/api/reviews/top` | public | Top 5 reviews |
| GET  | `/api/profile` | ✅ | Profile + premium status |
| PUT  | `/api/profile` | ✅ | Update display_name / email / phone / sms_enabled |
| POST | `/api/ai/summary` | ✅ Premium | Pasted text → 5 bullets |
| POST | `/api/ai/flashcards` | ✅ Premium | Pasted text → 6 cards |
| POST | `/api/ai/quiz` | ✅ Premium | Pasted text → 5 MCQs |
| POST | `/api/ai/concepts` | ✅ Premium | Titles[] → clusters |
| POST | `/api/ai/streak-coach` | ✅ Premium | Streak stats → 1 motivating line |

All Premium-gated endpoints return **HTTP 402** when the user is not currently
Premium — the frontend already handles this gracefully.

---

## 🛠️ Files in this delivery

```
learnflow/
├── CHANGES.md                          ← this file
├── backend/
│   ├── premium_routes.py               ← NEW · main blueprint
│   ├── twilio_helper.py                ← NEW · CLI tester
│   └── app_patch.md                    ← how to wire into app.py + SQL
└── frontend/
    ├── tailwind.config.js              ← REPLACE
    └── src/
        ├── index.css                   ← REPLACE
        ├── main.jsx                    ← REPLACE
        ├── App.jsx                     ← REPLACE
        ├── hooks/
        │   └── useAuth.jsx             ← REPLACE
        ├── services/
        │   └── api.jsx                 ← NEW (move/replace services/api.jsx)
        ├── components/
        │   ├── Footer.jsx              ← NEW
        │   ├── LoadingScreen.jsx       ← REPLACE
        │   ├── Navbar.jsx              ← REPLACE
        │   └── PremiumBadge.jsx        ← NEW
        └── pages/
            ├── Landing.jsx             ← NEW
            ├── Pricing.jsx             ← NEW
            ├── Payment.jsx             ← NEW
            ├── Profile.jsx             ← NEW
            ├── PremiumLab.jsx          ← NEW
            ├── Login.jsx               ← REPLACE
            ├── Register.jsx            ← REPLACE
            ├── Dashboard.jsx           ← REPLACE
            ├── Upload.jsx              ← REPLACE
            ├── Upcoming.jsx            ← REPLACE
            ├── History.jsx             ← REPLACE
            └── TodayTasks.jsx          ← REPLACE
```

Components from your original project I did NOT touch (still work as-is):
`RevisionCard.jsx`, `StatsCard.jsx`, `EmptyState.jsx` — they were only used inside
the old Dashboard, which has been replaced. You can safely delete them or keep them
around.

---

## 🌈 The marketing strategy baked into the redesign

1. **Free trial that doesn't ask for a card** → removes #1 reason students drop off at checkout.
2. **Coupon ritual** → the act of *typing* `LAUNCH30` increases perceived value (psych. ownership).
3. **Calm pastel + slow animations** → contrast with "study apps that feel like a to-do list from hell". Students share apps that *feel* good on their phone.
4. **Gemini-scored top reviews** → only the most articulate, specific testimonials reach the landing page. Stronger social proof = more conversions.
5. **Streak coach with kind tone** → no shaming. Makes the app feel like a friend, not a manager. Students re-open it tomorrow.
6. **Predictable navbar (5 items, same order, always)** → cognitive load drops. Power users glide; new users learn in one day.
7. **SMS at 8 AM + 9 PM** → bookends the day. The morning nudge does the work; the night nudge celebrates it.

---

## 🚀 Next ideas (NOT in this drop — propose if you want)

- WhatsApp via Twilio (same flow, different channel) for Indian students.
- Referral codes ("invite a friend → both get 7 more Premium days").
- Streak freeze (1 per week, prevents demotivation).
- Mobile PWA install banner.
- Anki export of generated flashcards.

Happy launching 🚀
