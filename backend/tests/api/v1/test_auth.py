import pytest
from datetime import timedelta
from fastapi import status

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.schemas import Token, User


def test_login_success(client, test_user):
    """Test successful login with correct credentials."""
    login_data = {
        "username": test_user.email,
        "password": "test123password",  # Must match the password in conftest.py
    }
    response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_200_OK, f"Login failed: {response.text}"
    
    data = response.json()
    assert "access_token" in data, "Access token not in response"
    assert "refresh_token" in data, "Refresh token not in response"
    assert data["token_type"] == "bearer", "Unexpected token type"


def test_login_incorrect_password(client, test_user):
    """Test login with incorrect password."""
    login_data = {
        "username": test_user.email,
        "password": "wrongpassword",  # Incorrect password
    }
    response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, \
        f"Expected 400 for incorrect password, got {response.status_code}: {response.text}"
    assert "Incorrect email or password" in response.json()["detail"], \
        "Expected error message for incorrect password"


def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "password123",
    }
    response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, \
        f"Expected 400 for non-existent user, got {response.status_code}: {response.text}"
    assert "Incorrect email or password" in response.json()["detail"], \
        "Expected error message for non-existent user"


def test_test_token_valid(client, test_user):
    """Test accessing a protected endpoint with a valid token."""
    # First log in to get a valid token
    login_data = {
        "username": test_user.email,
        "password": "password123",  # Must match the password in conftest.py
    }
    login_response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == status.HTTP_200_OK, \
        f"Login failed: {login_response.text}"
    
    access_token = login_response.json()["access_token"]
    
    # Test the token with the test-token endpoint
    response = client.post(
        "/api/v1/auth/login/test-token",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == status.HTTP_200_OK, \
        f"Test token endpoint failed: {response.text}"
    
    user_data = response.json()
    assert user_data["email"] == test_user.email, \
        "User email in response does not match test user"


def test_test_token_invalid(client):
    """Test accessing a protected endpoint with an invalid token."""
    response = client.post(
        "/api/v1/auth/login/test-token",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
        f"Expected 401 for invalid token, got {response.status_code}"
    assert "Could not validate credentials" in response.json()["detail"], \
        "Expected error message for invalid token"


def test_refresh_token(client, test_user, db):
    """Test refreshing an access token with a valid refresh token."""
    from app.models.session import Session
    
    # Clean up any existing sessions for this test user by deleting them
    db.query(Session).filter(Session.user_id == test_user.id).delete()
    db.commit()
    
    # First, log in to get a refresh token
    login_data = {
        "username": test_user.email,
        "password": "password123",
    }
    login_response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == status.HTTP_200_OK, \
        f"Login failed: {login_response.text}"
    
    refresh_token = login_response.json().get("refresh_token")
    assert refresh_token is not None, "No refresh token in login response"
    
    # Now use the refresh token to get a new access token
    response = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": refresh_token},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status.HTTP_200_OK, \
        f"Refresh token request failed: {response.text}"
    
    token_data = response.json()
    assert "access_token" in token_data, "No access token in refresh response"
    assert token_data["token_type"] == "bearer", "Unexpected token type"
    assert len(token_data["access_token"]) > 0, "Empty access token"


def test_logout(client, test_user):
    """Test logging out by revoking a refresh token."""
    # First, log in to get a refresh token
    login_data = {
        "username": test_user.email,
        "password": "password123",
    }
    login_response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == status.HTTP_200_OK, \
        f"Login failed: {login_response.text}"
    
    refresh_token = login_response.json().get("refresh_token")
    assert refresh_token is not None, "No refresh token in login response"
    
    # Now log out
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status.HTTP_200_OK, \
        f"Logout failed: {response.text}"
    assert response.json().get("msg") == "Successfully logged out", \
        "Unexpected logout message"
    
    # Verify the refresh token is no longer valid
    refresh_response = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": refresh_token},
        headers={"Content-Type": "application/json"}
    )
    # The actual implementation might return 400 or 401, both are acceptable for invalid refresh token
    assert refresh_response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED), \
        f"Expected 400 or 401 for revoked token, got {refresh_response.status_code}"
    assert "Could not validate credentials" in refresh_response.json().get("detail", ""), \
        "Expected error message for invalid refresh token"
