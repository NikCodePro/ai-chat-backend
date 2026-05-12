# API Documentation: Auth & Signup Flow

All API endpoints are prefixed with `/api/v1`.

## 📱 Phone/Email Signup Flow

The signup process is split into 3 steps to ensure verification before account creation.

### 1. Initiate Signup
**Endpoint:** `POST /auth/signup/initiate`  
**Description:** Sends an OTP to the provided phone number or email.

**Request Body:**
```json
{
  "identifier": "+919876543210" // or "user@example.com"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "OTP sent successfully",
  "data": {
    "message": "OTP sent to +919876543210",
    "identifier": "+919876543210",
    "expires_at": "2026-05-13T01:45:00Z"
  }
}
```

---

### 2. Verify Signup OTP
**Endpoint:** `POST /auth/signup/verify`  
**Description:** Verifies the OTP and returns a secure `signup_token`.

**Request Body:**
```json
{
  "identifier": "+919876543210",
  "code": "123456"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "data": {
    "message": "OTP verified successfully",
    "signup_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "identifier": "+919876543210"
  }
}
```

---

### 3. Complete Signup
**Endpoint:** `POST /auth/signup/complete`  
**Description:** Sets the username, password, and name using the `signup_token`.

**Request Body:**
```json
{
  "signup_token": "...", // Token received in step 2
  "name": "John Doe",
  "username": "johndoe_99",
  "password": "strongpassword123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "user": {
      "id": "645f...",
      "name": "John Doe",
      "username": "johndoe_99",
      "email": null,
      "phone": "+919876543210",
      "phone_verified": true,
      "created_at": "..."
    },
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
}
```

---

## 🔑 Login & Session Management

### 1. Standard Login
**Endpoint:** `POST /auth/login`  
**Description:** Login using username, email, or phone.

**Request Body:**
```json
{
  "identifier": "johndoe_99", // can be username, email, or phone
  "password": "strongpassword123"
}
```

**Response (Success):**
Returns the same structure as **Complete Signup**.

**Response (If 2FA Required):**
If phone 2FA is enabled, the API returns a challenge instead of tokens.
```json
{
  "success": true,
  "message": "Phone OTP verification required",
  "data": {
    "requires_2fa": true,
    "otp": { ... }
  }
}
```

---

### 2. Verify Login 2FA
**Endpoint:** `POST /auth/login/otp/verify`  
**Description:** Verifies the 2FA OTP after a successful password check.

**Request Body:**
```json
{
  "identifier": "+919876543210",
  "code": "123456",
  "password": "strongpassword123"
}
```

---

### 3. Token Refresh
**Endpoint:** `POST /auth/refresh`  
**Description:** Get a new access token using a valid refresh token.

**Request Body:**
```json
{
  "refresh_token": "..."
}
```

---

### 4. Logout
**Endpoint:** `POST /auth/logout`  
**Description:** Revokes the provided refresh token.

**Request Body:**
```json
{
  "refresh_token": "..."
}
```

---

### 5. Get Current User
**Endpoint:** `GET /auth/me`  
**Description:** Fetches the profile of the currently authenticated user.  
**Header:** `Authorization: Bearer <access_token>`
