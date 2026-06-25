"""Run the main StockFlow API flow against a local running instance."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "admin.smoke@example.com"
ADMIN_PASSWORD = "Admin12345"
VIEWER_PASSWORD = "Viewer12345"


class SmokeTestError(RuntimeError):
    """Raised when a smoke test step fails."""


def ok(message: str) -> None:
    print(f"[OK] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)


def response_detail(response: httpx.Response) -> str:
    try:
        return str(response.json())
    except ValueError:
        return response.text or "<empty response>"


def request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    expected_status: int,
    token: str | None = None,
    **kwargs: Any,
) -> httpx.Response:
    headers = dict(kwargs.pop("headers", {}))
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    response = client.request(method, path, headers=headers, **kwargs)
    if response.status_code != expected_status:
        raise SmokeTestError(
            f"{method} {path} returned {response.status_code}, "
            f"expected {expected_status}: {response_detail(response)}"
        )
    return response


def login(client: httpx.Client, email: str, password: str) -> str:
    response = request(
        client,
        "POST",
        "/api/v1/auth/login",
        expected_status=200,
        json={"email": email, "password": password},
    )
    token = response.json().get("access_token")
    if not token:
        raise SmokeTestError(f"Login response for {email} has no access token")
    return str(token)


def ensure_admin() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        password_hash = hash_password(ADMIN_PASSWORD)

        if admin is None:
            admin = User(
                email=ADMIN_EMAIL,
                hashed_password=password_hash,
                full_name="Smoke Test Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            action = "created"
        else:
            admin.hashed_password = password_hash
            admin.role = UserRole.ADMIN
            admin.is_active = True
            action = "ensured"

        db.commit()
    ok(f"ADMIN user {action} directly in the database")


def run() -> None:
    unique = uuid4().hex
    viewer_email = f"viewer.smoke.{unique}@example.com"
    sku = f"SMOKE-SKU-{unique}"
    warehouse_code = f"SMOKE-WH-{unique}"
    order_number = f"SMOKE-ORDER-{unique}"

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        health = request(client, "GET", "/api/v1/health", expected_status=200).json()
        if health.get("status") != "ok":
            raise SmokeTestError(f"Health response is not healthy: {health}")
        ok("Health check passed")

        viewer = request(
            client,
            "POST",
            "/api/v1/auth/register",
            expected_status=201,
            json={
                "email": viewer_email,
                "password": VIEWER_PASSWORD,
                "full_name": "Smoke Test Viewer",
            },
        ).json()
        if viewer.get("role") != "VIEWER":
            raise SmokeTestError(f"Registered user is not VIEWER: {viewer}")
        ok("Unique VIEWER user registered")

        viewer_token = login(client, viewer_email, VIEWER_PASSWORD)
        ok("VIEWER login passed")

        current_viewer = request(
            client,
            "GET",
            "/api/v1/auth/me",
            expected_status=200,
            token=viewer_token,
        ).json()
        if current_viewer.get("email") != viewer_email:
            raise SmokeTestError(f"/auth/me returned another user: {current_viewer}")
        ok("VIEWER /auth/me passed")

        request(
            client,
            "POST",
            "/api/v1/products",
            expected_status=403,
            token=viewer_token,
            json={"sku": sku, "name": "Forbidden Smoke Product"},
        )
        ok("VIEWER product creation rejected with 403")

        ensure_admin()
        admin_token = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        ok("ADMIN login passed")

        product = request(
            client,
            "POST",
            "/api/v1/products",
            expected_status=201,
            token=admin_token,
            json={"sku": sku, "name": "Smoke Test Product"},
        ).json()
        product_id = product["id"]
        ok(f"Product created with id={product_id}")

        warehouse = request(
            client,
            "POST",
            "/api/v1/warehouses",
            expected_status=201,
            token=admin_token,
            json={"code": warehouse_code, "name": "Smoke Test Warehouse"},
        ).json()
        warehouse_id = warehouse["id"]
        ok(f"Warehouse created with id={warehouse_id}")

        request(
            client,
            "POST",
            "/api/v1/stock/movements",
            expected_status=201,
            token=admin_token,
            json={
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "movement_type": "IN",
                "quantity": 10,
                "note": "Smoke test initial stock",
            },
        )
        ok("IN stock movement of 10 created")

        order = request(
            client,
            "POST",
            "/api/v1/orders",
            expected_status=201,
            token=admin_token,
            json={
                "order_number": order_number,
                "customer_name": "Smoke Test Customer",
                "items": [
                    {
                        "product_id": product_id,
                        "warehouse_id": warehouse_id,
                        "quantity": 3,
                    }
                ],
            },
        ).json()
        order_id = order["id"]
        ok(f"Order created with id={order_id}")

        reserved_order = request(
            client,
            "POST",
            f"/api/v1/orders/{order_id}/reserve",
            expected_status=200,
            token=admin_token,
        ).json()
        if reserved_order.get("status") != "RESERVED":
            raise SmokeTestError(f"Order was not reserved: {reserved_order}")
        ok("Order reserved")

        confirmed_order = request(
            client,
            "POST",
            f"/api/v1/orders/{order_id}/confirm",
            expected_status=200,
            token=admin_token,
        ).json()
        if confirmed_order.get("status") != "CONFIRMED":
            raise SmokeTestError(f"Order was not confirmed: {confirmed_order}")
        ok("Order confirmed")

        stock = request(
            client,
            "GET",
            "/api/v1/stock",
            expected_status=200,
            params={"product_id": product_id, "warehouse_id": warehouse_id},
        ).json()
        stock_items = stock.get("items", [])
        if len(stock_items) != 1 or stock_items[0].get("quantity") != 7:
            raise SmokeTestError(f"Expected final stock quantity 7: {stock}")
        ok("Final stock quantity is 7")

        movements = request(
            client,
            "GET",
            "/api/v1/stock/movements",
            expected_status=200,
            params={
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "limit": 100,
            },
        ).json()
        movement_types = {
            item.get("movement_type") for item in movements.get("items", [])
        }
        if not {"IN", "OUT"}.issubset(movement_types):
            raise SmokeTestError(
                f"Expected IN and OUT stock movements, got: {movements}"
            )
        ok("Stock movements contain IN and OUT")


def main() -> int:
    print(f"Running StockFlow API smoke test against {BASE_URL}")
    try:
        run()
    except (httpx.HTTPError, SmokeTestError, KeyError, ValueError) as exc:
        fail(str(exc))
        return 1
    except Exception as exc:
        fail(f"Unexpected error: {exc}")
        return 1

    print("[SUCCESS] StockFlow API smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
