# Backend Endpoint Testing Guide

## Prerequisites
- Backend server running (local or production)
- Valid JWT token (obtain from `/api/auth/login` or `/api/auth/register`)
- Supabase database configured with migrations applied
- Environment variables set (see `.env.example`)

## Authentication Endpoints

### 1. Register User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```
**Expected**: 201 with token and user info
**Rate Limit**: 5/hour

### 2. Login User
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```
**Expected**: 200 with token and user info
**Rate Limit**: 10/hour

### 3. Get Current User (JWT Required)
```bash
curl -X GET http://localhost:5000/api/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with user info including drive_connected status

### 4. Google OAuth (Get Auth URL)
```bash
curl -X GET "http://localhost:5000/api/auth/google?mode=login"
```
**Expected**: 200 with auth_url

### 5. Google OAuth Callback
- Test via browser by completing OAuth flow
- **Expected**: Redirect to dashboard with token

## Google Drive Endpoints

### 6. Connect Drive (JWT Required)
```bash
curl -X GET http://localhost:5000/api/drive/connect \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with auth_url
- Follow URL to complete OAuth
- **Expected**: Redirect to dashboard with drive=connected

### 7. Disconnect Drive (JWT Required)
```bash
curl -X POST http://localhost:5000/api/drive/disconnect \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with success message

## Upload Endpoints

### 8. Upload Preview (JWT Required)
```bash
curl -X POST http://localhost:5000/api/upload/preview \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@test.pdf"
```
**Expected**: 200 with generated heading and description
**Rate Limit**: 20/hour

### 9. Save Learning (JWT Required)
```bash
curl -X POST http://localhost:5000/api/upload/save \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "heading": "Test Learning",
    "description": "Test description",
    "source": "manual",
    "url": "",
    "supabase_path": "",
    "filename": ""
  }'
```
**Expected**: 201 with learning_id and drive_link (if Drive connected)

## Revision Endpoints

### 10. Get Today's Revisions (JWT Required)
```bash
curl -X GET http://localhost:5000/api/revisions/today \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with revisions array

### 11. Get Overdue Revisions (JWT Required)
```bash
curl -X GET http://localhost:5000/api/revisions/overdue \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with revisions array

### 12. Complete Revision (JWT Required)
```bash
curl -X POST http://localhost:5000/api/revisions/complete/REVISION_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with success message

### 13. Postpone Revision (JWT Required)
```bash
curl -X POST http://localhost:5000/api/revisions/postpone/REVISION_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with new scheduled date

### 14. Get Revision Stats (JWT Required)
```bash
curl -X GET http://localhost:5000/api/revisions/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with stats (completed, pending, streak)

### 15. Get History (JWT Required)
```bash
curl -X GET http://localhost:5000/api/revisions/history \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with completed revisions

## AI Artifacts Endpoints (Premium Required)

### 16. Generate AI Artifacts (JWT + Premium Required)
```bash
curl -X POST http://localhost:5000/api/ai/generate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "learning_id": 1,
    "types": ["summary", "keywords", "quiz", "flashcards", "mindmap", "revision_notes"]
  }'
```
**Expected**: 200 with generated artifacts
**Rate Limit**: 10/hour

### 17. Get AI Artifacts (JWT Required)
```bash
curl -X GET http://localhost:5000/api/ai/artifacts/LEARNING_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with stored artifacts

## Notification Endpoints

### 18. Enable SMS Notifications (JWT Required)
```bash
curl -X POST http://localhost:5000/api/notifications/enable \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "enabled": true,
    "timezone": "UTC",
    "notification_hour": 8
  }'
```
**Expected**: 200 with SMS settings

### 19. Get Notification Preferences (JWT Required)
```bash
curl -X GET http://localhost:5000/api/notifications/preferences \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with notification settings

### 20. Send Daily Notifications (Cron Job - Secret Required)
```bash
curl -X POST http://localhost:5000/api/notifications/send-daily \
  -H "X-Notification-Secret: YOUR_SECRET" \
  -H "Content-Type: application/json"
```
**Expected**: 200 with sent/skipped counts
**Rate Limit**: 10/hour

## Premium Endpoints

### 21. Get Premium Status (JWT Required)
```bash
curl -X GET http://localhost:5000/api/premium/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
**Expected**: 200 with premium status

### 22. Redeem Premium Coupon (JWT Required)
```bash
curl -X POST http://localhost:5000/api/premium/redeem \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "+1234567890",
    "coupon": "LAUNCH30"
  }'
```
**Expected**: 200 with receipt (or 400 if invalid/already redeemed)

## Health Check

### 23. Health Check
```bash
curl -X GET http://localhost:5000/health
```
**Expected**: 200 with service status

## Testing Checklist

### Authentication
- [ ] Register new user
- [ ] Login with correct credentials
- [ ] Login with incorrect credentials (should fail)
- [ ] Get current user info
- [ ] Google OAuth flow (manual browser test)

### Google Drive
- [ ] Connect Drive (manual OAuth flow)
- [ ] Verify drive_connected=true in /api/me
- [ ] Upload file and verify Drive upload
- [ ] Disconnect Drive
- [ ] Verify drive_connected=false in /api/me

### Upload & Revisions
- [ ] Upload preview with file
- [ ] Upload preview with URL
- [ ] Upload preview with text
- [ ] Save learning material
- [ ] Get today's revisions
- [ ] Get overdue revisions
- [ ] Complete a revision
- [ ] Postpone a revision
- [ ] Get revision stats
- [ ] Get history

### AI Features (Premium)
- [ ] Redeem valid coupon
- [ ] Try to redeem invalid coupon (should fail)
- [ ] Try to redeem same coupon twice (should fail)
- [ ] Generate AI artifacts (summary)
- [ ] Generate AI artifacts (keywords)
- [ ] Generate AI artifacts (quiz)
- [ ] Generate AI artifacts (flashcards)
- [ ] Generate AI artifacts (mindmap)
- [ ] Generate AI artifacts (revision notes)
- [ ] Generate all artifacts at once
- [ ] Retrieve stored artifacts

### Notifications
- [ ] Enable SMS notifications
- [ ] Get notification preferences
- [ ] Test cron job (with secret)

### Error Handling
- [ ] Test with invalid JWT (should fail)
- [ ] Test with no JWT on protected routes (should fail)
- [ ] Test rate limiting (exceed limits)
- [ ] Test invalid learning_id
- [ ] Test invalid pagination params

### Security Headers
- [ ] Verify Content-Security-Policy header
- [ ] Verify X-Frame-Options header
- [ ] Verify X-Content-Type-Options header
- [ ] Verify X-XSS-Protection header
- [ ] Verify Referrer-Policy header

## Common Issues

### JWT Token Issues
- Ensure token is correctly formatted: `Bearer YOUR_TOKEN`
- Check token expiration (default 7 days)
- Verify FLASK_SECRET_KEY is set

### Drive Connection Issues
- Verify GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET
- Check redirect URIs in Google Cloud Console
- Ensure Drive API is enabled
- Check SCOPES include drive.file

### AI Generation Issues
- Verify GEMINI_API_KEY is set
- Check user has premium status
- Verify learning_id exists and belongs to user
- Check rate limit (10/hour)

### SMS Issues
- Verify TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_PHONE
- Check phone number format (+country code)
- Verify DAILY_NOTIFICATION_SECRET for cron job
- Check notification_hour is valid (0-23)

### Database Issues
- Ensure migrations are applied in order
- Check Supabase connection (SUPABASE_URL, SUPABASE_KEY)
- Verify table schemas match migrations
- Check foreign key constraints

## Performance Testing

### Load Testing (Optional)
```bash
# Install Apache Bench
ab -n 1000 -c 10 http://localhost:5000/health

# Test rate limiting
for i in {1..15}; do
  curl -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'
done
```

## Notes

- Replace `YOUR_JWT_TOKEN` with actual token from login
- Replace `LEARNING_ID` with actual learning ID from save response
- Replace `REVISION_ID` with actual revision ID
- Replace `YOUR_SECRET` with DAILY_NOTIFICATION_SECRET env var
- All protected endpoints require valid JWT in Authorization header
- Rate limits reset on server restart (in-memory storage)
