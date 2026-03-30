import pytest
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_create_and_get_note(client):
    payload = {
        "title": "Test note",
        "description": "A test description",
        "owner": "Alice",
        "group_tag": "Sprint 1",
        "wake_date": (date.today() + timedelta(days=5)).isoformat(),
        "urgency": "medium",
        "tags": ["backend", "urgent"]
    }
    res = await client.post("/api/notes", json=payload)
    assert res.status_code == 201
    note = res.json()
    assert note["title"] == "Test note"
    assert note["description"] == "A test description"
    assert note["owner"] == "Alice"
    assert note["group_tag"] == "Sprint 1"
    assert note["urgency"] == "medium"
    assert note["tags"] == ["backend", "urgent"]
    assert note["resolved"] is False
    assert "id" in note
    assert "created_at" in note
    assert "updated_at" in note

    # GET by id
    res2 = await client.get(f"/api/notes/{note['id']}")
    assert res2.status_code == 200
    assert res2.json()["id"] == note["id"]


@pytest.mark.asyncio
async def test_list_notes(client):
    # Create two notes
    for i in range(2):
        await client.post("/api/notes", json={
            "title": f"Note {i}",
            "owner": "Bob",
            "group_tag": "Team A",
            "wake_date": (date.today() + timedelta(days=i)).isoformat(),
            "urgency": "low",
            "tags": []
        })

    res = await client.get("/api/notes")
    assert res.status_code == 200
    notes = res.json()
    assert len(notes) == 2


@pytest.mark.asyncio
async def test_update_note(client):
    payload = {
        "title": "Original title",
        "owner": "Charlie",
        "group_tag": "Group X",
        "wake_date": (date.today() + timedelta(days=10)).isoformat(),
        "urgency": "low",
        "tags": ["old"]
    }
    res = await client.post("/api/notes", json=payload)
    note_id = res.json()["id"]

    # Update title and urgency
    res2 = await client.patch(f"/api/notes/{note_id}", json={
        "title": "Updated title",
        "urgency": "high",
        "tags": ["new", "updated"]
    })
    assert res2.status_code == 200
    updated = res2.json()
    assert updated["title"] == "Updated title"
    assert updated["urgency"] == "high"
    assert updated["tags"] == ["new", "updated"]
    # Other fields unchanged
    assert updated["owner"] == "Charlie"


@pytest.mark.asyncio
async def test_delete_note(client):
    res = await client.post("/api/notes", json={
        "title": "To be deleted",
        "owner": "Dave",
        "group_tag": "Group Y",
        "wake_date": (date.today() + timedelta(days=3)).isoformat(),
        "urgency": "low",
        "tags": []
    })
    note_id = res.json()["id"]

    res2 = await client.delete(f"/api/notes/{note_id}")
    assert res2.status_code == 204

    # Verify it's gone
    res3 = await client.get(f"/api/notes/{note_id}")
    assert res3.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client):
    res = await client.delete("/api/notes/nonexistent-id")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_resolve_note(client):
    res = await client.post("/api/notes", json={
        "title": "Will resolve",
        "owner": "Eve",
        "group_tag": "Group Z",
        "wake_date": (date.today() + timedelta(days=2)).isoformat(),
        "urgency": "medium",
        "tags": []
    })
    note_id = res.json()["id"]

    res2 = await client.post(f"/api/notes/{note_id}/resolve")
    assert res2.status_code == 200
    assert res2.json()["resolved"] is True


@pytest.mark.asyncio
async def test_resolved_notes_endpoint(client):
    # Create and immediately resolve
    res = await client.post("/api/notes", json={
        "title": "Archived note",
        "owner": "Frank",
        "group_tag": "Archive",
        "wake_date": (date.today() + timedelta(days=1)).isoformat(),
        "urgency": "high",
        "tags": []
    })
    note_id = res.json()["id"]
    await client.post(f"/api/notes/{note_id}/resolve")

    res2 = await client.get("/api/notes/resolved")
    assert res2.status_code == 200
    resolved = res2.json()
    assert len(resolved) == 1
    assert resolved[0]["title"] == "Archived note"
    assert resolved[0]["resolved"] is True


@pytest.mark.asyncio
async def test_groups_endpoint(client):
    await client.post("/api/notes", json={
        "title": "Note 1",
        "owner": "Alice",
        "group_tag": "Alpha",
        "wake_date": (date.today() + timedelta(days=5)).isoformat(),
        "urgency": "low",
        "tags": []
    })
    await client.post("/api/notes", json={
        "title": "Note 2",
        "owner": "Bob",
        "group_tag": "Beta",
        "wake_date": (date.today() + timedelta(days=3)).isoformat(),
        "urgency": "low",
        "tags": []
    })
    await client.post("/api/notes", json={
        "title": "Note 3",
        "owner": "Charlie",
        "group_tag": "Alpha",
        "wake_date": (date.today() + timedelta(days=1)).isoformat(),
        "urgency": "low",
        "tags": []
    })

    res = await client.get("/api/groups")
    assert res.status_code == 200
    groups = res.json()
    assert set(groups) == {"Alpha", "Beta"}


@pytest.mark.asyncio
async def test_tags_endpoint(client):
    await client.post("/api/notes", json={
        "title": "Note with tags",
        "owner": "Alice",
        "group_tag": "Team",
        "wake_date": (date.today() + timedelta(days=5)).isoformat(),
        "urgency": "low",
        "tags": ["python", "fastapi"]
    })
    await client.post("/api/notes", json={
        "title": "Another with tags",
        "owner": "Bob",
        "group_tag": "Team",
        "wake_date": (date.today() + timedelta(days=3)).isoformat(),
        "urgency": "low",
        "tags": ["fastapi", "uvicorn"]
    })

    res = await client.get("/api/tags")
    assert res.status_code == 200
    tags = res.json()
    assert set(tags) == {"python", "fastapi", "uvicorn"}


@pytest.mark.asyncio
async def test_export_endpoint(client):
    await client.post("/api/notes", json={
        "title": "Export me",
        "owner": "George",
        "group_tag": "ExportGroup",
        "wake_date": (date.today() + timedelta(days=7)).isoformat(),
        "urgency": "high",
        "tags": ["exported"]
    })

    res = await client.get("/api/export")
    assert res.status_code == 200
    data = res.json()
    assert "notes" in data
    assert len(data["notes"]) == 1
    assert data["notes"][0]["title"] == "Export me"


@pytest.mark.asyncio
async def test_import_endpoint(client):
    payload = {
        "notes": [
            {
                "title": "Imported note 1",
                "description": "From export",
                "owner": "Importer",
                "group_tag": "Imported",
                "wake_date": (date.today() + timedelta(days=4)).isoformat(),
                "urgency": "medium",
                "tags": ["imported"],
                "resolved": False
            },
            {
                "title": "Imported note 2",
                "owner": "Importer",
                "group_tag": "Imported",
                "wake_date": (date.today() + timedelta(days=6)).isoformat(),
                "urgency": "low",
                "tags": [],
                "resolved": True
            }
        ]
    }

    res = await client.post("/api/import", json=payload)
    assert res.status_code == 200
    result = res.json()
    assert result["imported"] == 2

    # Verify both notes exist
    notes_res = await client.get("/api/notes")
    active = notes_res.json()
    assert len(active) == 1
    assert active[0]["title"] == "Imported note 1"

    resolved_res = await client.get("/api/notes/resolved")
    resolved = resolved_res.json()
    assert len(resolved) == 1
    assert resolved[0]["title"] == "Imported note 2"


@pytest.mark.asyncio
async def test_update_note_not_found(client):
    res = await client.patch("/api/notes/nonexistent", json={"title": "New title"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_note_not_found(client):
    res = await client.get("/api/notes/nonexistent")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_import_invalid_payload(client):
    res = await client.post("/api/import", json={"notes": "not a list"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_note_without_description(client):
    """Notes with no description should work fine."""
    payload = {
        "title": "Minimal note",
        "owner": "Minimalist",
        "group_tag": "Bare",
        "wake_date": (date.today() + timedelta(days=2)).isoformat(),
        "urgency": "low",
        "tags": []
    }
    res = await client.post("/api/notes", json=payload)
    assert res.status_code == 201
    note = res.json()
    assert note["description"] is None
    assert note["title"] == "Minimal note"


@pytest.mark.asyncio
async def test_serve_index(client):
    """GET / should return the frontend HTML."""
    res = await client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Prikbord" in res.text
