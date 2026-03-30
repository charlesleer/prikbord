from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from models import NoteCreate, NoteOut, NoteUpdate
from database import (
    create_note,
    delete_note,
    get_all_notes,
    get_all_tags,
    get_groups,
    get_note,
    get_notes,
    get_resolved_notes,
    import_notes,
    init_db,
    resolve_note,
    update_note,
)

app = FastAPI()


@app.on_event("startup")
async def startup():
    await init_db()


static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def serve_index():
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/api/notes", response_model=list[NoteOut])
async def list_notes():
    return await get_notes()


@app.post("/api/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create(note: NoteCreate):
    result = await create_note(
        title=note.title,
        description=note.description,
        owner=note.owner,
        group_tag=note.group_tag,
        wake_date=note.wake_date.isoformat(),
        urgency=note.urgency.value,
        tags=note.tags,
    )
    return result


@app.get("/api/notes/resolved", response_model=list[NoteOut])
async def list_resolved():
    return await get_resolved_notes()


@app.get("/api/notes/{note_id}", response_model=NoteOut)
async def get_one(note_id: str):
    note = await get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.patch("/api/notes/{note_id}", response_model=NoteOut)
async def update_one(note_id: str, note: NoteUpdate):
    existing = await get_note(note_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Note not found")
    update_data = note.model_dump(exclude_unset=True)
    if "wake_date" in update_data and update_data["wake_date"] is not None:
        update_data["wake_date"] = update_data["wake_date"].isoformat()
    if "urgency" in update_data and update_data["urgency"] is not None:
        update_data["urgency"] = update_data["urgency"].value
    result = await update_note(note_id, **update_data)
    return result


@app.delete("/api/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one(note_id: str):
    deleted = await delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")


@app.post("/api/notes/{note_id}/resolve", response_model=NoteOut)
async def resolve_one(note_id: str):
    note = await get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return await resolve_note(note_id)


@app.get("/api/groups")
async def list_groups():
    return await get_groups()


@app.get("/api/tags")
async def list_tags():
    return await get_all_tags()


@app.get("/api/export")
async def export_notes():
    """Export all notes (active and resolved) as JSON."""
    notes = await get_all_notes()
    return JSONResponse(content={"notes": notes})


@app.post("/api/import")
async def import_notes_endpoint(data: Dict[str, Any]):
    """Import notes from JSON. Returns count of imported notes."""
    notes = data.get("notes", [])
    if not isinstance(notes, list):
        raise HTTPException(status_code=400, detail="notes must be a list")
    result = await import_notes(notes)
    return result
