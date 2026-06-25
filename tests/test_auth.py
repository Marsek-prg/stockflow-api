import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


def register_user(
    client: TestClient,
    *,
    email: str = "viewer@example.com",
    password: str = "viewer-password",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test Viewer",
        },
    )
    assert response.status_code == 201
    return response.json()


def login(
    client: TestClient,
    *,
    email: str = "viewer@example.com",
    password: str = "viewer-password",
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    return response.json()["access_token"]


def create_user(
    db: Session,
    *,
    email: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("secure-password"),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def test_register_success(anonymous_client: TestClient) -> None:
    body = register_user(anonymous_client)

    assert body["email"] == "viewer@example.com"
    assert body["full_name"] == "Test Viewer"
    assert body["role"] == "VIEWER"
    assert body["is_active"] is True
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(
    anonymous_client: TestClient,
) -> None:
    register_user(anonymous_client)

    response = anonymous_client.post(
        "/api/v1/auth/register",
        json={
            "email": "VIEWER@example.com",
            "password": "another-password",
        },
    )

    assert response.status_code == 409


def test_login_success(anonymous_client: TestClient) -> None:
    register_user(anonymous_client)

    token = login(anonymous_client)

    assert token


def test_login_wrong_password_returns_401(
    anonymous_client: TestClient,
) -> None:
    register_user(anonymous_client)

    response = anonymous_client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_with_token_success(anonymous_client: TestClient) -> None:
    registered = register_user(anonymous_client)
    token = login(anonymous_client)

    response = anonymous_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]


def test_me_without_token_returns_401(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_inactive_user_cannot_authenticate_or_access_protected_endpoint(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    register_user(anonymous_client)
    token = login(anonymous_client)
    user = db_session.query(User).filter_by(email="viewer@example.com").one()
    user.is_active = False
    db_session.commit()

    login_response = anonymous_client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-password"},
    )
    me_response = anonymous_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert login_response.status_code == 401
    assert me_response.status_code == 401


def test_admin_can_list_users(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        email="admin@example.com",
        role=UserRole.ADMIN,
    )

    response = anonymous_client.get("/api/v1/users", headers=auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_admin_can_get_user(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        email="admin@example.com",
        role=UserRole.ADMIN,
    )
    viewer = create_user(
        db_session,
        email="viewer@example.com",
        role=UserRole.VIEWER,
    )

    response = anonymous_client.get(
        f"/api/v1/users/{viewer.id}",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "viewer@example.com"


def test_admin_can_update_user(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        email="admin@example.com",
        role=UserRole.ADMIN,
    )
    viewer = create_user(
        db_session,
        email="viewer@example.com",
        role=UserRole.VIEWER,
    )

    response = anonymous_client.patch(
        f"/api/v1/users/{viewer.id}",
        json={
            "email": "manager@example.com",
            "full_name": "Warehouse Manager",
            "role": "MANAGER",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "manager@example.com"
    assert response.json()["full_name"] == "Warehouse Manager"
    assert response.json()["role"] == "MANAGER"


def test_admin_can_soft_delete_user(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    admin = create_user(
        db_session,
        email="admin@example.com",
        role=UserRole.ADMIN,
    )
    viewer = create_user(
        db_session,
        email="viewer@example.com",
        role=UserRole.VIEWER,
    )

    response = anonymous_client.delete(
        f"/api/v1/users/{viewer.id}",
        headers=auth_headers(admin),
    )
    db_session.refresh(viewer)

    assert response.status_code == 204
    assert viewer.is_active is False


def test_viewer_cannot_list_users(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    viewer = create_user(
        db_session,
        email="viewer@example.com",
        role=UserRole.VIEWER,
    )

    response = anonymous_client.get("/api/v1/users", headers=auth_headers(viewer))

    assert response.status_code == 403


def test_protected_write_endpoint_without_token_returns_401(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/api/v1/products",
        json={"sku": "AUTH-001", "name": "Protected product"},
    )

    assert response.status_code == 401


def test_protected_write_endpoint_with_viewer_returns_403(
    anonymous_client: TestClient,
    db_session: Session,
) -> None:
    viewer = create_user(
        db_session,
        email="viewer@example.com",
        role=UserRole.VIEWER,
    )

    response = anonymous_client.post(
        "/api/v1/products",
        json={"sku": "AUTH-001", "name": "Protected product"},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 403


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.ADMIN])
def test_protected_write_endpoint_with_manager_or_admin_succeeds(
    anonymous_client: TestClient,
    db_session: Session,
    role: UserRole,
) -> None:
    user = create_user(
        db_session,
        email=f"{role.value.lower()}@example.com",
        role=role,
    )

    response = anonymous_client.post(
        "/api/v1/products",
        json={"sku": f"{role.value}-001", "name": "Protected product"},
        headers=auth_headers(user),
    )

    assert response.status_code == 201
