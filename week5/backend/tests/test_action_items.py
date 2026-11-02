def test_create_and_complete_action_item(client):
    payload = {"description": "Ship it"}
    r = client.post("/action-items/", json=payload)
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["completed"] is False

    r = client.put(f"/action-items/{item['id']}/complete")
    assert r.status_code == 200
    done = r.json()
    assert done["completed"] is True

    r = client.get("/action-items/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["completed"] is True


def test_action_items_pagination_boundaries(client):
    for i in range(15):
        r = client.post("/action-items/", json={"description": f"task-{i}"})
        assert r.status_code == 201, r.text

    r = client.get("/action-items/", params={"page": 2, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2
    assert body["page_size"] == 5
    assert body["total"] == 15
    assert len(body["items"]) == 5

    # Empty last page
    r = client.get("/action-items/", params={"page": 50, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 15
    assert body["items"] == []

    # Too-large page_size clamped to 100
    r = client.get("/action-items/", params={"page": 1, "page_size": 500})
    assert r.status_code == 200
    body = r.json()
    assert body["page_size"] == 100
    assert len(body["items"]) == 15