# Authentication System Documentation

## Overview
This document provides a comprehensive guide to the authentication system implemented in the Healthcare Integration Engine. The system uses JWT (JSON Web Tokens) for stateless authentication, with support for access and refresh tokens.

## Table of Contents
1. [Authentication Flow](#authentication-flow)
2. [Token Management](#token-management)
3. [Security Considerations](#security-considerations)
4. [API Endpoints](#api-endpoints)
5. [Database Schema](#database-schema)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Testing](#testing)

## Authentication Flow

### 1. User Login
1. Client sends username/password to `/auth/login/access-token`
2. Server validates credentials
3. On success, issues:
   - Access token (short-lived, 30 minutes)
   - Refresh token (long-lived, 7 days)
   - Both tokens are stored in the database

### 2. Accessing Protected Resources
1. Client includes `Authorization: Bearer <access_token>` in request headers
2. Server validates token and grants access if valid

### 3. Token Refresh
1. When access token expires, client sends refresh token to `/auth/refresh-token`
2. Server validates refresh token
3. If valid, issues new access token
4. Optionally rotates refresh token (currently disabled)

### 4. Logout
1. Client sends refresh token to `/auth/logout`
2. Server marks the session as revoked
3. Client removes tokens from storage

## Token Management

### Access Token
- **Type**: JWT
- **Lifetime**: 30 minutes
- **Contents**:
  ```json
  {
    "sub": "user_id",
    "type": "access",
    "exp": 1234567890
  }
  ```

### Refresh Token
- **Type**: JWT
- **Lifetime**: 7 days
- **Storage**: Database (sessions table)
- **Contents**:
  ```json
  {
    "sub": "user_id",
    "type": "refresh",
    "exp": 1234567890
  }
  ```

## Security Considerations

### Token Security
- Tokens are signed using HS256 algorithm
- Never store sensitive data in tokens
- Access tokens are short-lived (30 minutes)
- Refresh tokens can be revoked

### Session Management
- Each login creates a new session
- Sessions can be individually revoked
- Automatic cleanup of expired sessions recommended

### Rate Limiting
- Implement rate limiting on login endpoints
- Consider IP-based rate limiting for failed attempts

## API Endpoints

### POST /auth/login/access-token
- **Description**: Authenticate user and get tokens
- **Request**:
  ```json
  {
    "username": "user@example.com",
    "password": "string"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "bearer"
  }
  ```

### POST /auth/refresh-token
- **Description**: Refresh access token
- **Request**:
  ```json
  {
    "refresh_token": "string"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "bearer"
  }
  ```

### POST /auth/logout
- **Description**: Revoke refresh token
- **Request**:
  ```json
  {
    "refresh_token": "string"
  }
  ```
- **Response**:
  ```json
  {
    "msg": "Successfully logged out"
  }
  ```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(512) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration

### Required Environment Variables
```env
# JWT Configuration
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app

# Redis (for future rate limiting)
REDIS_HOST=redis
REDIS_PORT=6379
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
- Invalid request format
- Missing required fields

#### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

#### 403 Forbidden
- Insufficient permissions
- Revoked token

#### 404 Not Found
- User not found
- Resource not found

## Testing

### Unit Tests
1. Test token creation and validation
2. Test authentication endpoints
3. Test session management
4. Test error conditions

### Integration Tests
1. Test complete authentication flow
2. Test token refresh
3. Test concurrent sessions
4. Test rate limiting

## Future Improvements
1. Implement token rotation for refresh tokens
2. Add MFA support
3. Add password complexity requirements
4. Implement account lockout after failed attempts
5. Add session management UI
6. Implement OAuth2 providers (Google, GitHub, etc.)
