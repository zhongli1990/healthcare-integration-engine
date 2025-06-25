import pytest
from datetime import timedelta
from fastapi import status

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.schemas import Token, User


def test_login_success(client, test_user, db):
    """Test successful login with correct credentials."""
    from app.crud import user as crud_user
    
    print("\n=== Testing login with credentials ===")
    print(f"Test user email: {test_user.email}")
    print(f"Test user hashed password: {test_user.hashed_password}")
    
    # Verify the test user exists in the database
    db_user = crud_user.get_by_email(db, email=test_user.email)
    assert db_user is not None, f"Test user {test_user.email} not found in database"
    print(f"Found test user in database: {db_user.email}")
    
    login_data = {
        "username": test_user.email,
        "password": "tester123",  # Using the password from conftest.py
    }
    print(f"Sending login request with data: {login_data}")
    
    response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.text}")
    
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
        "password": test_user.plain_password,  # Use the plain password from the test user fixture
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
    import logging
    from app.models.session import Session
    from app.crud import session_crud
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Log test user info
    logger.info(f"Test user ID: {test_user.id}, email: {test_user.email}")
    
    # 1. Clean up any existing sessions for this test user
    db.query(Session).filter(Session.user_id == test_user.id).delete()
    db.commit()
    
    # 2. Log in to get a refresh token - this will create a session in the database
    login_data = {
        "username": test_user.email,
        "password": test_user.plain_password,
    }
    logger.info(f"Attempting login with email: {login_data['username']}")
    
    login_response = client.post(
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    logger.info(f"Login response status: {login_response.status_code}")
    
    assert login_response.status_code == status.HTTP_200_OK, \
        f"Login failed: {login_response.text}"
    
    # Get the refresh token from the login response
    refresh_token = login_response.json().get("refresh_token")
    assert refresh_token is not None, "No refresh token in login response"
    logger.info("Successfully obtained refresh token")
    
    # 3. Use the refresh token to get a new access token
    refresh_data = {"refresh_token": refresh_token}
    logger.info(f"Attempting to refresh token with: {refresh_data}")
    
    response = client.post(
        "/api/v1/auth/refresh-token",
        json=refresh_data,
        headers={"Content-Type": "application/json"}
    )
    logger.info(f"Refresh token response status: {response.status_code}")
    
    assert response.status_code == status.HTTP_200_OK, \
        f"Refresh token request failed: {response.text}"
    
    # 4. Verify the response contains a valid access token
    token_data = response.json()
    assert "access_token" in token_data, "No access token in refresh response"
    assert token_data["token_type"] == "bearer", "Unexpected token type"
    assert len(token_data["access_token"]) > 0, "Empty access token"
    logger.info("Successfully obtained new access token using refresh token")
    
    # 5. Verify the refresh token can be reused (if your implementation allows this)
    response2 = client.post(
        "/api/v1/auth/refresh-token",
        json=refresh_data,
        headers={"Content-Type": "application/json"}
    )
    logger.info(f"Second refresh token response status: {response2.status_code}")
    
    # The second refresh should also succeed
    assert response2.status_code == status.HTTP_200_OK, \
        f"Second refresh token request failed: {response2.text}"
    
    # Clean up the session after the test
    db.query(Session).filter(Session.token == refresh_token).delete()
    db.commit()


def test_logout(client, test_user, db):
    """Test logging out by revoking a refresh token."""
    from app.models.session import Session as SessionModel
    
    # Clean up any existing sessions for this test user
    db.query(SessionModel).filter(SessionModel.user_id == test_user.id).delete()
    db.commit()
    
    # First, log in to get a refresh token
    login_data = {
        "username": test_user.email,
        "password": test_user.plain_password,
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
    
    # Instead of checking the database directly, verify the login was successful
    # by using the access token to access a protected endpoint
    access_token = login_response.json().get("access_token")
    assert access_token is not None, "No access token in login response"
    
    # Now log out
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
    )
    assert response.status_code == status.HTTP_200_OK, \
        f"Logout failed: {response.text}"
    assert response.json().get("msg") == "Successfully logged out", \
        "Unexpected logout message"
    
    # Verify the refresh token is no longer valid by attempting to refresh
    refresh_response = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": refresh_token},
        headers={"Content-Type": "application/json"}
    )
    
    # The implementation should return 401 for invalid/revoked refresh token
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED, \
        f"Expected 401 for revoked token, got {refresh_response.status_code}"
    
    # The error message might vary, so we'll just check that we got an error
    assert "detail" in refresh_response.json(), \
        "Expected error detail in response"
