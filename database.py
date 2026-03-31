import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite

DB_PATH = Path(__file__).parent / "prikbord.db"
MAX_TAG_LENGTH = 50


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                owner TEXT NOT NULL,
                group_tag TEXT NOT NULL,
                wake_date TEXT,
                urgency TEXT NOT NULL DEFAULT 'low',
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0
            )
        """)
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
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "resolved": bool(row["resolved"]),
    }


async def create_note(
    title: str,
    description: Optional[str],
    owner: str,
    group_tag: str,
    wake_date: Optional[str],
    urgency: str = "low",
    tags: Optional[List[str]] = None,
) -> dict:
    now = datetime.utcnow().isoformat()
    note_id = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO notes (id, title, description, owner, group_tag, wake_date, urgency, tags, created_at, updated_at, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (note_id, title, description, owner, group_tag, wake_date, urgency, tags_json, now, now),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = await cursor.fetchone()
    return _row_to_note(row)


async def get_notes() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notes WHERE resolved = 0 ORDER BY wake_date ASC"
        )
        rows = await cursor.fetchall()
    return [_row_to_note(row) for row in rows]


async def get_resolved_notes() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notes WHERE resolved = 1 ORDER BY updated_at DESC"
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


async def get_groups() -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT DISTINCT group_tag FROM notes ORDER BY group_tag"
        )
        rows = await cursor.fetchall()
    return [row["group_tag"] for row in rows]


async def get_all_tags() -> List[str]:
    """Get all unique tags across all notes."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT tags FROM notes")
        rows = await cursor.fetchall()
    tag_set = set()
    for row in rows:
        tags = json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"]
        for tag in tags:
            tag_set.add(tag)
    return sorted(tag_set)


async def get_all_notes() -> List[dict]:
    """Get all notes (active and resolved) for export."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM notes ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    return [_row_to_note(row) for row in rows]


async def import_notes(notes: List[dict]) -> dict:
    """Import a list of notes. Creates new notes with new IDs."""
    imported = 0
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for note in notes:
            note_id = str(uuid.uuid4())
            tags = note.get("tags", [])
            if isinstance(tags, list):
                tags = [str(t)[:MAX_TAG_LENGTH] for t in tags[:20]]  # cap 20 tags, 50 chars each
                tags = json.dumps(tags)
            await db.execute(
                """
                INSERT INTO notes (id, title, description, owner, group_tag, wake_date, urgency, tags, created_at, updated_at, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    note.get("created_at", now),
                    now,
                    1 if note.get("resolved") else 0,
                ),
            )
            imported += 1
        await db.commit()
    return {"imported": imported}
