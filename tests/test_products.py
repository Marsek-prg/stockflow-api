from fastapi.testclient import TestClient


def create_product(
    client: TestClient,
    sku: str = "SKU-001",
    name: str = "First product",
) -> dict:
    response = client.post(
        "/api/v1/products",
        json={"sku": sku, "name": name, "description": "Description"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_product_success(client: TestClient) -> None:
    product = create_product(client)

    assert product["id"] == 1
    assert product["sku"] == "SKU-001"
    assert product["unit"] == "pcs"
    assert product["is_active"] is True
    assert product["created_at"]
    assert product["updated_at"]


def test_create_product_duplicate_sku_returns_409(client: TestClient) -> None:
    create_product(client)

    response = client.post(
        "/api/v1/products", json={"sku": "SKU-001", "name": "Duplicate"}
    )

    assert response.status_code == 409


def test_create_product_rejects_blank_sku_and_name(client: TestClient) -> None:
    response = client.post("/api/v1/products", json={"sku": "  ", "name": ""})

    assert response.status_code == 422


def test_list_products_returns_items_and_pagination(client: TestClient) -> None:
    create_product(client, "SKU-001", "First")
    create_product(client, "SKU-002", "Second")

    response = client.get("/api/v1/products?limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["sku"] == "SKU-002"
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1


def test_search_product_by_sku_and_name(client: TestClient) -> None:
    create_product(client, "BLUE-001", "Blue widget")
    create_product(client, "RED-002", "Red component")

    by_sku = client.get("/api/v1/products?search=blue")
    by_name = client.get("/api/v1/products?search=COMPONENT")

    assert [item["sku"] for item in by_sku.json()["items"]] == ["BLUE-001"]
    assert [item["sku"] for item in by_name.json()["items"]] == ["RED-002"]


def test_get_product_by_id(client: TestClient) -> None:
    product = create_product(client)

    response = client.get(f"/api/v1/products/{product['id']}")

    assert response.status_code == 200
    assert response.json()["sku"] == product["sku"]


def test_update_product(client: TestClient) -> None:
    product = create_product(client)

    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"name": "Updated product", "unit": "box"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated product"
    assert response.json()["unit"] == "box"


def test_delete_product_soft_deactivates_it(client: TestClient) -> None:
    product = create_product(client)

    delete_response = client.delete(f"/api/v1/products/{product['id']}")
    get_response = client.get(f"/api/v1/products/{product['id']}")
    inactive_response = client.get("/api/v1/products?is_active=false")

    assert delete_response.status_code == 204
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False
    assert inactive_response.json()["total"] == 1
    assert client.delete(f"/api/v1/products/{product['id']}").status_code == 404


def test_get_missing_product_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/products/999")

    assert response.status_code == 404
