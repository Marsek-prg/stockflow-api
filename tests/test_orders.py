from fastapi.testclient import TestClient


def create_product(client: TestClient, sku: str = "SKU-001") -> dict:
    response = client.post(
        "/api/v1/products",
        json={"sku": sku, "name": f"Product {sku}"},
    )
    assert response.status_code == 201
    return response.json()


def create_warehouse(client: TestClient, code: str = "WH-001") -> dict:
    response = client.post(
        "/api/v1/warehouses",
        json={"code": code, "name": f"Warehouse {code}"},
    )
    assert response.status_code == 201
    return response.json()


def add_stock(
    client: TestClient, product_id: int, warehouse_id: int, quantity: int
) -> None:
    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "movement_type": "IN",
            "quantity": quantity,
        },
    )
    assert response.status_code == 201


def create_order(
    client: TestClient,
    product_id: int,
    warehouse_id: int,
    *,
    order_number: str = "ORD-001",
    quantity: int = 2,
) -> dict:
    response = client.post(
        "/api/v1/orders",
        json={
            "order_number": order_number,
            "customer_name": "Example Customer",
            "note": "Deliver carefully",
            "items": [
                {
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "quantity": quantity,
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def setup_inventory(client: TestClient, quantity: int = 10) -> tuple[dict, dict]:
    product = create_product(client)
    warehouse = create_warehouse(client)
    add_stock(client, product["id"], warehouse["id"], quantity)
    return product, warehouse


def test_create_order_success(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)

    order = create_order(client, product["id"], warehouse["id"])

    assert order["order_number"] == "ORD-001"
    assert order["status"] == "DRAFT"
    assert order["customer_name"] == "Example Customer"
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2
    assert order["reservations"] == []


def test_create_order_with_empty_items_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/orders",
        json={"order_number": "ORD-001", "items": []},
    )

    assert response.status_code == 422


def test_reserve_order_success(client: TestClient) -> None:
    product, warehouse = setup_inventory(client)
    order = create_order(client, product["id"], warehouse["id"], quantity=4)

    response = client.post(f"/api/v1/orders/{order['id']}/reserve")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RESERVED"
    assert len(body["reservations"]) == 1
    assert body["reservations"][0]["status"] == "ACTIVE"
    assert body["reservations"][0]["quantity"] == 4
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 10


def test_reserve_with_insufficient_available_stock_returns_409(
    client: TestClient,
) -> None:
    product, warehouse = setup_inventory(client, quantity=5)
    first = create_order(
        client,
        product["id"],
        warehouse["id"],
        order_number="ORD-001",
        quantity=4,
    )
    second = create_order(
        client,
        product["id"],
        warehouse["id"],
        order_number="ORD-002",
        quantity=2,
    )
    assert client.post(f"/api/v1/orders/{first['id']}/reserve").status_code == 200

    response = client.post(f"/api/v1/orders/{second['id']}/reserve")

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient available stock"
    assert client.get(f"/api/v1/orders/{second['id']}").json()["status"] == "DRAFT"


def test_reserve_already_reserved_order_returns_409(client: TestClient) -> None:
    product, warehouse = setup_inventory(client)
    order = create_order(client, product["id"], warehouse["id"])
    assert client.post(f"/api/v1/orders/{order['id']}/reserve").status_code == 200

    response = client.post(f"/api/v1/orders/{order['id']}/reserve")

    assert response.status_code == 409


def test_confirm_reserved_order_creates_out_movements_and_consumes_reservations(
    client: TestClient,
) -> None:
    product, warehouse = setup_inventory(client, quantity=10)
    order = create_order(client, product["id"], warehouse["id"], quantity=3)
    assert client.post(f"/api/v1/orders/{order['id']}/reserve").status_code == 200

    response = client.post(f"/api/v1/orders/{order['id']}/confirm")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CONFIRMED"
    assert body["reservations"][0]["status"] == "CONSUMED"
    stock = client.get("/api/v1/stock").json()
    assert stock["items"][0]["quantity"] == 7
    movements = client.get("/api/v1/stock/movements?movement_type=OUT").json()
    assert movements["total"] == 1
    assert movements["items"][0]["quantity"] == 3
    assert movements["items"][0]["balance_before"] == 10
    assert movements["items"][0]["balance_after"] == 7


def test_confirming_same_order_twice_returns_409(client: TestClient) -> None:
    product, warehouse = setup_inventory(client)
    order = create_order(client, product["id"], warehouse["id"])
    assert client.post(f"/api/v1/orders/{order['id']}/reserve").status_code == 200
    assert client.post(f"/api/v1/orders/{order['id']}/confirm").status_code == 200

    response = client.post(f"/api/v1/orders/{order['id']}/confirm")

    assert response.status_code == 409
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "CONFIRMED"
    assert client.get("/api/v1/stock/movements?movement_type=OUT").json()["total"] == 1


def test_cancel_draft_order_success(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    order = create_order(client, product["id"], warehouse["id"])

    response = client.post(f"/api/v1/orders/{order['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["reservations"] == []


def test_cancel_reserved_order_releases_reservations(client: TestClient) -> None:
    product, warehouse = setup_inventory(client)
    order = create_order(client, product["id"], warehouse["id"])
    assert client.post(f"/api/v1/orders/{order['id']}/reserve").status_code == 200

    response = client.post(f"/api/v1/orders/{order['id']}/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CANCELLED"
    assert body["reservations"][0]["status"] == "RELEASED"
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 10


def test_cancel_reserved_order_makes_stock_available_for_another_order(
    client: TestClient,
) -> None:
    product, warehouse = setup_inventory(client, quantity=5)
    first = create_order(
        client,
        product["id"],
        warehouse["id"],
        order_number="ORD-001",
        quantity=5,
    )
    second = create_order(
        client,
        product["id"],
        warehouse["id"],
        order_number="ORD-002",
        quantity=5,
    )
    assert client.post(f"/api/v1/orders/{first['id']}/reserve").status_code == 200
    assert client.post(f"/api/v1/orders/{second['id']}/reserve").status_code == 409

    cancel_response = client.post(f"/api/v1/orders/{first['id']}/cancel")
    reserve_response = client.post(f"/api/v1/orders/{second['id']}/reserve")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["reservations"][0]["status"] == "RELEASED"
    assert reserve_response.status_code == 200
    assert reserve_response.json()["status"] == "RESERVED"
    assert reserve_response.json()["reservations"][0]["status"] == "ACTIVE"


def test_reserve_multiple_items_is_atomic_when_one_has_insufficient_stock(
    client: TestClient,
) -> None:
    first_product = create_product(client, "SKU-001")
    second_product = create_product(client, "SKU-002")
    warehouse = create_warehouse(client)
    add_stock(client, first_product["id"], warehouse["id"], 10)
    add_stock(client, second_product["id"], warehouse["id"], 1)
    create_response = client.post(
        "/api/v1/orders",
        json={
            "order_number": "ORD-MULTI",
            "items": [
                {
                    "product_id": first_product["id"],
                    "warehouse_id": warehouse["id"],
                    "quantity": 5,
                },
                {
                    "product_id": second_product["id"],
                    "warehouse_id": warehouse["id"],
                    "quantity": 2,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    order = create_response.json()

    reserve_response = client.post(f"/api/v1/orders/{order['id']}/reserve")
    get_response = client.get(f"/api/v1/orders/{order['id']}")

    assert reserve_response.status_code == 409
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "DRAFT"
    assert get_response.json()["reservations"] == []


def test_confirmed_order_cannot_be_cancelled(client: TestClient) -> None:
    product, warehouse = setup_inventory(client)
    order = create_order(client, product["id"], warehouse["id"])
    assert client.post(f"/api/v1/orders/{order['id']}/reserve").status_code == 200
    assert client.post(f"/api/v1/orders/{order['id']}/confirm").status_code == 200

    response = client.post(f"/api/v1/orders/{order['id']}/cancel")

    assert response.status_code == 409
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "CONFIRMED"


def test_list_orders_with_status_filter(client: TestClient) -> None:
    product, warehouse = setup_inventory(client)
    draft = create_order(
        client,
        product["id"],
        warehouse["id"],
        order_number="ORD-DRAFT",
    )
    reserved = create_order(
        client,
        product["id"],
        warehouse["id"],
        order_number="ORD-RESERVED",
    )
    assert client.post(f"/api/v1/orders/{reserved['id']}/reserve").status_code == 200

    response = client.get("/api/v1/orders?status=RESERVED")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["items"][0]["id"] == reserved["id"]
    assert body["items"][0]["status"] == "RESERVED"
    assert body["items"][0]["id"] != draft["id"]


def test_get_missing_order_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/orders/999")

    assert response.status_code == 404
