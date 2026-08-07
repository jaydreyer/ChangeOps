def test_request_id_is_preserved_on_api_response(client) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "deployment-smoke-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "deployment-smoke-123"


def test_unsafe_request_id_is_replaced(client) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "unsafe value"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "unsafe value"
    assert len(response.headers["X-Request-ID"]) == 36
