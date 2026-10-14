def test_create_and_list_notes(client):
    payload = {"title": "Test", "content": "Hello world"}
    r = client.post("/notes/", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Test"

    r = client.get("/notes/")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1

    r = client.get("/notes/search/")
    assert r.status_code == 200

    r = client.get("/notes/search/", params={"q": "Hello"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1


def test_search_notes_case_insensitive(client):
    client.post("/notes/", json={"title": "Greeting", "content": "Hello World"})
    client.post("/notes/", json={"title": "Other", "content": "nothing here"})

    r = client.get("/notes/search/", params={"q": "hello"})
    assert r.status_code == 200
    contents = [n["content"] for n in r.json()]
    assert "Hello World" in contents
    assert "nothing here" not in contents

    r = client.get("/notes/search/", params={"q": "GREETING"})
    assert r.status_code == 200
    titles = [n["title"] for n in r.json()]
    assert titles == ["Greeting"]


def test_search_notes_empty_query_returns_all(client):
    client.post("/notes/", json={"title": "A", "content": "one"})
    client.post("/notes/", json={"title": "B", "content": "two"})

    r = client.get("/notes/search/", params={"q": ""})
    assert r.status_code == 200
    assert len(r.json()) == 2
