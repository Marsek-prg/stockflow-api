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


def create_movement(
    client: TestClient,
    product_id: int,
    warehouse_id: int,
    movement_type: str,
    quantity: int,
    note: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "movement_type": movement_type,
            "quantity": quantity,
            "note": note,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_in_creates_stock_item_and_movement(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)

    movement = create_movement(
        client, product["id"], warehouse["id"], "IN", 10, "Initial receipt"
    )
    stock = client.get("/api/v1/stock").json()

    assert movement["balance_before"] == 0
    assert movement["balance_after"] == 10
    assert movement["note"] == "Initial receipt"
    assert stock["total"] == 1
    assert stock["items"][0]["quantity"] == 10


def test_in_increases_existing_stock(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    create_movement(client, product["id"], warehouse["id"], "IN", 10)

    movement = create_movement(client, product["id"], warehouse["id"], "IN", 4)

    assert movement["balance_before"] == 10
    assert movement["balance_after"] == 14
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 14


def test_out_decreases_stock(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    create_movement(client, product["id"], warehouse["id"], "IN", 10)

    movement = create_movement(client, product["id"], warehouse["id"], "OUT", 3)

    assert movement["balance_before"] == 10
    assert movement["balance_after"] == 7
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 7


def test_out_with_insufficient_stock_returns_409(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    create_movement(client, product["id"], warehouse["id"], "IN", 2)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "movement_type": "OUT",
            "quantity": 3,
        },
    )

    assert response.status_code == 409
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 2
    assert client.get("/api/v1/stock/movements").json()["total"] == 1


def test_out_without_existing_stock_returns_409_and_creates_no_stock_item(
    client: TestClient,
) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "movement_type": "OUT",
            "quantity": 1,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient stock"
    assert client.get("/api/v1/stock").json()["total"] == 0
    assert client.get("/api/v1/stock/movements").json()["total"] == 0


def test_in_with_negative_quantity_returns_422(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "movement_type": "IN",
            "quantity": -1,
        },
    )

    assert response.status_code == 422


def test_out_with_negative_quantity_returns_422(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    create_movement(client, product["id"], warehouse["id"], "IN", 5)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "movement_type": "OUT",
            "quantity": -2,
        },
    )

    assert response.status_code == 422
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 5


def test_adjustment_with_negative_quantity_returns_422(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "movement_type": "ADJUSTMENT",
            "quantity": -1,
        },
    )

    assert response.status_code == 422


def test_adjustment_with_zero_quantity_is_allowed(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    create_movement(client, product["id"], warehouse["id"], "IN", 5)

    movement = create_movement(
        client,
        product["id"],
        warehouse["id"],
        "ADJUSTMENT",
        0,
    )

    assert movement["balance_before"] == 5
    assert movement["balance_after"] == 0
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 0


def test_adjustment_sets_exact_stock_quantity(client: TestClient) -> None:
    product = create_product(client)
    warehouse = create_warehouse(client)
    create_movement(client, product["id"], warehouse["id"], "IN", 10)

    movement = create_movement(client, product["id"], warehouse["id"], "ADJUSTMENT", 4)

    assert movement["balance_before"] == 10
    assert movement["balance_after"] == 4
    assert client.get("/api/v1/stock").json()["items"][0]["quantity"] == 4


def test_missing_product_returns_404(client: TestClient) -> None:
    warehouse = create_warehouse(client)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": 999,
            "warehouse_id": warehouse["id"],
            "movement_type": "IN",
            "quantity": 1,
        },
    )

    assert response.status_code == 404


def test_missing_warehouse_returns_404(client: TestClient) -> None:
    product = create_product(client)

    response = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": product["id"],
            "warehouse_id": 999,
            "movement_type": "IN",
            "quantity": 1,
        },
    )

    assert response.status_code == 404


def test_list_stock_items_with_pagination(client: TestClient) -> None:
    product = create_product(client)
    first_warehouse = create_warehouse(client, "WH-001")
    second_warehouse = create_warehouse(client, "WH-002")
    create_movement(client, product["id"], first_warehouse["id"], "IN", 5)
    create_movement(client, product["id"], second_warehouse["id"], "IN", 8)

    response = client.get(f"/api/v1/stock?product_id={product['id']}&limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["warehouse_id"] == second_warehouse["id"]


def test_list_stock_movements_with_filters(client: TestClient) -> None:
    first_product = create_product(client, "SKU-001")
    second_product = create_product(client, "SKU-002")
    warehouse = create_warehouse(client)
    create_movement(client, first_product["id"], warehouse["id"], "IN", 10)
    create_movement(client, first_product["id"], warehouse["id"], "OUT", 2)
    create_movement(client, second_product["id"], warehouse["id"], "IN", 7)

    response = client.get(
        "/api/v1/stock/movements"
        f"?product_id={first_product['id']}"
        f"&warehouse_id={warehouse['id']}"
        "&movement_type=OUT"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["items"][0]["movement_type"] == "OUT"
    assert body["items"][0]["quantity"] == 2
