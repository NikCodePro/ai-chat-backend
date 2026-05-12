# AI Chat Backend

FastAPI backend for an AI chat app with MongoDB, JWT auth, refresh tokens, and a realtime-ready project layout.

## Tech Stack

- FastAPI
- MongoDB with Motor
- JWT access tokens and refresh tokens
- Passlib + bcrypt password hashing
- Pydantic settings from `.env`

## Setup

```bash
pip install -r requirements.txt
```

Update `.env` with your MongoDB URI and secrets:

```env
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=ai_chat_app

JWT_SECRET_KEY=replace_with_a_strong_secret_key_at_least_32_chars
JWT_REFRESH_SECRET=replace_with_a_strong_refresh_secret_at_least_32_chars

ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
OTP_EXPIRE_MINUTES=10
OTP_LENGTH=6
RETURN_OTP_IN_RESPONSE=true
TWO_FACTOR_API_KEY=your_2factor_api_key
TWO_FACTOR_SMS_TIMEOUT_SECONDS=10
GOOGLE_CLIENT_ID=your_google_oauth_client_id
```

Run the API:

```bash
python main.py
```

The API will be available at:

```text
http://localhost:8000
```

Interactive docs:

```text
http://localhost:8000/docs
```

## API Prefix

All routes use:

```text
/api/v1
```

## Routes

```text
GET  /api/v1/health

POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/otp/request
POST /api/v1/auth/otp/verify
POST /api/v1/auth/login/otp/verify
POST /api/v1/auth/google
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me

GET  /api/v1/users/me
```

## Signup And Sign In

Register with email:

```json
{
  "name": "Nikhil",
  "email": "nikhil@example.com",
  "password": "Password123"
}
```

Register with phone:

```json
{
  "name": "Nikhil",
  "phone": "+919876543210",
  "password": "Password123"
}
```

Registration creates an OTP challenge. Verify it before treating the account as signed in:

```json
{
  "identifier": "nikhil@example.com",
  "code": "123456",
  "purpose": "signup"
}
```

Sign in with either email or phone:

```json
{
  "identifier": "nikhil@example.com",
  "password": "Password123"
}
```

Phone accounts use phone OTP as 2FA. If login returns `requires_2fa: true`, verify the login OTP:

```json
{
  "identifier": "+919876543210",
  "code": "123456",
  "password": "Password123",
  "purpose": "login_2fa"
}
```

Phone OTPs are sent through 2Factor's SMS OTP API. This backend uses SMS only, not voice/call OTP. Set `TWO_FACTOR_API_KEY` in `.env`; for production also set `RETURN_OTP_IN_RESPONSE=false` so OTP codes are not returned in API responses.

Continue with Google:

```json
{
  "id_token": "google_id_token_from_frontend"
}
```

## Auth Response Shape

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "...",
      "name": "...",
      "email": "...",
      "created_at": "..."
    },
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
}
```

## Token Expiration

- Access token: 24 hours
- Refresh token: 7 days

Refresh tokens are stored in MongoDB so logout and session revocation are supported.
