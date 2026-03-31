import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite

DB_PATH = Path(__file__).parent / "prikbord.db"
MAX_TAG_LENGTH = 50
DEFAULT_BOARD_ID = "default"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(f"""
            CREATE TABLE IF NOT EXISTS boards (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                owner TEXT NOT NULL,
                group_tag TEXT NOT NULL,
                wake_date TEXT,
                urgency TEXT NOT NULL DEFAULT 'low',
                tags TEXT NOT NULL DEFAULT '[]',
                board_id TEXT NOT NULL DEFAULT '{DEFAULT_BOARD_ID}',
                note_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (board_id) REFERENCES boards(id)
            )
        """)
        # Create default board if not exists
        now = datetime.utcnow().isoformat()
        await db.execute(
            f"INSERT OR IGNORE INTO boards (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (DEFAULT_BOARD_ID, "Main Board", now, now),
        )
        await db.commit()


def _row_to_note(row: aiosqlite.Row) -> dict:
    tags = row["tags"]
    if isinstance(tags, str):
        tags = json.loads(tags)
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "owner": row["owner"],
        "group_tag": row["group_tag"],
        "wake_date": row["wake_date"],
        "urgency": row["urgency"],
        "tags": tags,
        "board_id": row["board_id"],
        "note_order": row["note_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "resolved": bool(row["resolved"]),
    }


# ─── Boards ───────────────────────────────────────────────────────────────────

async def create_board(name: str) -> dict:
    now = datetime.utcnow().isoformat()
    board_id = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO boards (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (board_id, name, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM boards WHERE id = ?", (board_id,))
        row = await cursor.fetchone()
    return dict(row)


async def get_boards() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM boards ORDER BY created_at ASC")
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def rename_board(id: str, name: str) -> Optional[dict]:
    if id == DEFAULT_BOARD_ID:
        return None  # can't rename the default board
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE boards SET name = ?, updated_at = ? WHERE id = ?",
            (name, now, id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM boards WHERE id = ?", (id,))
        row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def delete_board(id: str) -> bool:
    if id == DEFAULT_BOARD_ID:
        return False  # can't delete the default board
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if board has any notes
        cursor = await db.execute(
            "SELECT COUNT(*) FROM notes WHERE board_id = ?", (id,)
        )
        count = (await cursor.fetchone())[0]
        if count > 0:
            return False  # board has notes, can't delete
        cursor = await db.execute("DELETE FROM boards WHERE id = ?", (id,))
        await db.commit()
    return cursor.rowcount > 0


# ─── Notes ─────────────────────────────────────────────────────────────────────

async def create_note(
    title: str,
    description: Optional[str],
    owner: str,
    group_tag: str,
    wake_date: Optional[str],
    urgency: str = "low",
    tags: Optional[List[str]] = None,
    board_id: str = DEFAULT_BOARD_ID,
    note_order: int = 0,
) -> dict:
    now = datetime.utcnow().isoformat()
    note_id = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO notes (id, title, description, owner, group_tag, wake_date, urgency, tags, board_id, note_order, created_at, updated_at, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (note_id, title, description, owner, group_tag, wake_date, urgency, tags_json, board_id, note_order, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = await cursor.fetchone()
    return _row_to_note(row)


async def get_notes(board_id: str = DEFAULT_BOARD_ID) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM notes WHERE resolved = 0 AND board_id = ?
            ORDER BY CASE WHEN wake_date IS NULL THEN 0 ELSE 1 END, note_order ASC, wake_date ASC""",
            (board_id,),
        )
        rows = await cursor.fetchall()
    return [_row_to_note(row) for row in rows]


async def get_resolved_notes(board_id: str = DEFAULT_BOARD_ID) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notes WHERE resolved = 1 AND board_id = ? ORDER BY updated_at DESC",
            (board_id,),
        )
        rows = await cursor.fetchall()
    return [_row_to_note(row) for row in rows]


async def get_note(id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM notes WHERE id = ?", (id,))
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_note(row)


async def update_note(id: str, **fields) -> Optional[dict]:
    if not fields:
        return await get_note(id)
    fields["updated_at"] = datetime.utcnow().isoformat()
    # Serialize tags to JSON if present
    if "tags" in fields and fields["tags"] is not None:
        fields["tags"] = json.dumps(fields["tags"])
    # board_id cannot be changed via this function
    fields.pop("board_id", None)
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE notes SET {set_clause} WHERE id = ?", values
        )
        await db.commit()
    return await get_note(id)


async def delete_note(id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM notes WHERE id = ?", (id,))
        await db.commit()
    return cursor.rowcount > 0


async def resolve_note(id: str) -> Optional[dict]:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE notes SET resolved = 1, updated_at = ? WHERE id = ?",
            (now, id),
        )
        await db.commit()
    return await get_note(id)


async def get_groups(board_id: str = DEFAULT_BOARD_ID) -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT DISTINCT group_tag FROM notes WHERE board_id = ? ORDER BY group_tag",
            (board_id,),
        )
        rows = await cursor.fetchall()
    return [row["group_tag"] for row in rows]


async def get_all_tags(board_id: str = DEFAULT_BOARD_ID) -> List[str]:
    """Get all unique tags across notes in a board."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT tags FROM notes WHERE board_id = ?", (board_id,)
        )
        rows = await cursor.fetchall()
    tag_set = set()
    for row in rows:
        tags = json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"]
        for tag in tags:
            tag_set.add(tag)
    return sorted(tag_set)


async def get_all_notes(board_id: str = DEFAULT_BOARD_ID) -> List[dict]:
    """Get all notes (active and resolved) for export."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notes WHERE board_id = ? ORDER BY created_at DESC",
            (board_id,),
        )
        rows = await cursor.fetchall()
    return [_row_to_note(row) for row in rows]


async def import_notes(notes: List[dict], board_id: str = DEFAULT_BOARD_ID) -> dict:
    """Import a list of notes. Creates new notes with new IDs."""
    imported = 0
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for note in notes:
            note_id = str(uuid.uuid4())
            tags = note.get("tags", [])
            if isinstance(tags, list):
                tags = [str(t)[:MAX_TAG_LENGTH] for t in tags[:20]]
                tags = json.dumps(tags)
            await db.execute(
                """
                INSERT INTO notes (id, title, description, owner, group_tag, wake_date, urgency, tags, board_id, note_order, created_at, updated_at, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note_id,
                    note.get("title", ""),
                    note.get("description"),
                    note.get("owner", ""),
                    note.get("group_tag", ""),
                    note.get("wake_date", ""),
                    note.get("urgency", "low"),
                    tags if isinstance(tags, str) else json.dumps(tags),
                    board_id,
                    0,
                    note.get("created_at", now),
                    now,
                    1 if note.get("resolved") else 0,
                ),
            )
            imported += 1
        await db.commit()
    return {"imported": imported}


async def update_note_order(note_orders: List[dict]) -> None:
    """Batch update note_order for a list of {id, note_order} pairs."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for item in note_orders:
            await db.execute(
                "UPDATE notes SET note_order = ?, updated_at = ? WHERE id = ?",
                (item["note_order"], now, item["id"]),
            )
        await db.commit()
