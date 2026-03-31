from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from models import BoardCreate, BoardOut, ImportPayload, NoteCreate, NoteOut, NoteUpdate
from database import (
    DEFAULT_BOARD_ID,
    create_board,
    create_note,
    delete_board,
    delete_note,
    get_all_notes,
    get_all_tags,
    get_boards,
    get_groups,
    get_note,
    get_notes,
    get_resolved_notes,
    import_notes,
    init_db,
    rename_board,
    resolve_note,
    update_note,
    update_note_order,
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


# ─── Boards ───────────────────────────────────────────────────────────────────

@app.get("/api/boards", response_model=list[BoardOut])
async def list_boards():
    return await get_boards()


@app.post("/api/boards", response_model=BoardOut, status_code=status.HTTP_201_CREATED)
async def create(board: BoardCreate):
    result = await create_board(name=board.name)
    return result


@app.patch("/api/boards/{board_id}", response_model=BoardOut)
async def update_board(board_id: str, board: BoardCreate):
    result = await rename_board(board_id, board.name)
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found or cannot rename default board")
    return result


@app.delete("/api/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_endpoint(board_id: str):
    deleted = await delete_board(board_id)
    if not deleted:
        raise HTTPException(
            status_code=409,
            detail="Board not found, is the default board, or has notes"
        )


# ─── Notes ─────────────────────────────────────────────────────────────────────

@app.get("/api/notes", response_model=list[NoteOut])
async def list_notes(board: str = Query(DEFAULT_BOARD_ID)):
    return await get_notes(board_id=board)


@app.post("/api/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create(note: NoteCreate, board: str = Query(DEFAULT_BOARD_ID)):
    result = await create_note(
        title=note.title,
        description=note.description,
        owner=note.owner,
        group_tag=note.group_tag,
        wake_date=note.wake_date.isoformat() if note.wake_date else None,
        urgency=note.urgency.value,
        tags=note.tags,
        board_id=board,
    )
    return result


@app.get("/api/notes/resolved", response_model=list[NoteOut])
async def list_resolved(board: str = Query(DEFAULT_BOARD_ID)):
    return await get_resolved_notes(board_id=board)


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
async def list_groups(board: str = Query(DEFAULT_BOARD_ID)):
    return await get_groups(board_id=board)


@app.get("/api/tags")
async def list_tags(board: str = Query(DEFAULT_BOARD_ID)):
    return await get_all_tags(board_id=board)


@app.get("/api/export")
async def export_notes(board: str = Query(DEFAULT_BOARD_ID)):
    """Export all notes (active and resolved) for the current board as JSON."""
    notes = await get_all_notes(board_id=board)
    return JSONResponse(content={"notes": notes})


@app.post("/api/import")
async def import_notes_endpoint(data: ImportPayload, board: str = Query(DEFAULT_BOARD_ID)):
    """Import notes from JSON into the current board. Returns count of imported notes."""
    result = await import_notes([n.model_dump() for n in data.notes], board_id=board)
    return result


@app.post("/api/notes/reorder")
async def reorder_notes(payload: list[dict]):
    """Batch update note_order for drag-reorder. payload = [{id, note_order}, ...]"""
    await update_note_order(payload)
    return {"ok": True}
