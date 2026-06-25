from fastapi.testclient import TestClient


def create_warehouse(
    client: TestClient,
    code: str = "WH-001",
    name: str = "Main warehouse",
) -> dict:
    response = client.post(
        "/api/v1/warehouses",
        json={"code": code, "name": name, "address": "1 Storage Street"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_warehouse_success(client: TestClient) -> None:
    warehouse = create_warehouse(client)

    assert warehouse["id"] == 1
    assert warehouse["code"] == "WH-001"
    assert warehouse["is_active"] is True
    assert warehouse["created_at"]
    assert warehouse["updated_at"]


def test_create_warehouse_duplicate_code_returns_409(client: TestClient) -> None:
    create_warehouse(client)

    response = client.post(
        "/api/v1/warehouses", json={"code": "WH-001", "name": "Duplicate"}
    )

    assert response.status_code == 409


def test_create_warehouse_rejects_blank_code_and_name(client: TestClient) -> None:
    response = client.post("/api/v1/warehouses", json={"code": "  ", "name": ""})

    assert response.status_code == 422


def test_list_warehouses_returns_items_and_pagination(client: TestClient) -> None:
    create_warehouse(client, "WH-001", "First")
    create_warehouse(client, "WH-002", "Second")

    response = client.get("/api/v1/warehouses?limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["code"] == "WH-002"
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1


def test_search_warehouse_by_code_and_name(client: TestClient) -> None:
    create_warehouse(client, "NORTH-01", "Northern depot")
    create_warehouse(client, "SOUTH-02", "Southern storage")

    by_code = client.get("/api/v1/warehouses?search=north")
    by_name = client.get("/api/v1/warehouses?search=STORAGE")

    assert [item["code"] for item in by_code.json()["items"]] == ["NORTH-01"]
    assert [item["code"] for item in by_name.json()["items"]] == ["SOUTH-02"]


def test_get_warehouse_by_id(client: TestClient) -> None:
    warehouse = create_warehouse(client)

    response = client.get(f"/api/v1/warehouses/{warehouse['id']}")

    assert response.status_code == 200
    assert response.json()["code"] == warehouse["code"]


def test_update_warehouse(client: TestClient) -> None:
    warehouse = create_warehouse(client)

    response = client.patch(
        f"/api/v1/warehouses/{warehouse['id']}",
        json={"name": "Updated warehouse", "address": "2 New Street"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated warehouse"
    assert response.json()["address"] == "2 New Street"


def test_delete_warehouse_soft_deactivates_it(client: TestClient) -> None:
    warehouse = create_warehouse(client)

    delete_response = client.delete(f"/api/v1/warehouses/{warehouse['id']}")
    get_response = client.get(f"/api/v1/warehouses/{warehouse['id']}")
    inactive_response = client.get("/api/v1/warehouses?is_active=false")

    assert delete_response.status_code == 204
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False
    assert inactive_response.json()["total"] == 1
    assert client.delete(f"/api/v1/warehouses/{warehouse['id']}").status_code == 404


def test_get_missing_warehouse_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/warehouses/999")

    assert response.status_code == 404
