def test_create_and_list_notes(client):
    payload = {"title": "Test", "content": "Hello world"}
    r = client.post("/notes/", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Test"
    assert "created_at" in data

    r = client.get("/notes/")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


def test_notes_pagination_boundaries(client):
    for i in range(12):
        r = client.post("/notes/", json={"title": f"N{i:02d}", "content": f"body {i}"})
        assert r.status_code == 201, r.text

    r = client.get("/notes/", params={"page": 2, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2
    assert body["page_size"] == 5
    assert body["total"] == 12
    assert len(body["items"]) == 5

    # Empty last page beyond available data
    r = client.get("/notes/", params={"page": 99, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 12
    assert body["items"] == []

    # Too-large page_size is clamped to 100
    r = client.get("/notes/", params={"page": 1, "page_size": 1000})
    assert r.status_code == 200
    body = r.json()
    assert body["page_size"] == 100
    assert len(body["items"]) == 12


def test_notes_search_pagination_and_sort(client):
    payloads = [
        {"title": "Alpha Plan", "content": "first match"},
        {"title": "Beta", "content": "ALPHA in content"},
        {"title": "Gamma", "content": "unrelated"},
        {"title": "alpha zebra", "content": "another"},
    ]
    for p in payloads:
        assert client.post("/notes/", json=p).status_code == 201

    # Case-insensitive match on title and content
    r = client.get("/notes/search", params={"q": "alpha", "page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert len(body["items"]) == 3

    # Trailing slash also works
    r = client.get("/notes/search/", params={"q": "alpha"})
    assert r.status_code == 200
    assert r.json()["total"] == 3

    # title_asc sort
    r = client.get(
        "/notes/search",
        params={"q": "alpha", "sort": "title_asc", "page_size": 10},
    )
    assert r.status_code == 200
    titles = [item["title"] for item in r.json()["items"]]
    assert titles == sorted(titles, key=str.lower)

    # created_desc (default): newest first — last inserted among matches is "alpha zebra"
    r = client.get(
        "/notes/search",
        params={"q": "alpha", "sort": "created_desc", "page_size": 10},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["title"] == "alpha zebra"

    # Pagination within search results
    r = client.get(
        "/notes/search",
        params={"q": "alpha", "page": 2, "page_size": 2, "sort": "title_asc"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1

    # Empty query returns all notes with envelope
    r = client.get("/notes/search", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2

    # No matches
    r = client.get("/notes/search", params={"q": "zzz-no-match"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []