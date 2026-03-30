# Prikbord

**Prikbord** is a lightweight, self-hosted shared awareness tool — a virtual pinboard for teams. Notes surface visually as their wake-up date approaches. The core principle: adding a note should feel as fast as slapping a post-it on a board.

## Features

- **Time-aware urgency** — notes glow amber (approaching), red (imminent), or pulse red (overdue) as their wake date nears
- **Grouping** — notes are organized by team, project, or topic with visual group headers
- **Multi-tag support** — tag notes freely, filter by any tag
- **Resolve / Archive** — soft-delete notes to an archive without losing context
- **Export / Import** — full JSON backup, great for migrating between instances or sharing board configs
- **Search** — filter instantly by title or owner
- **Keyboard-first** — `N` to add, `Esc` to close, `Enter` to confirm

## Quick Start

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 2345 --reload
```

Open [http://localhost:2345](http://localhost:2345). That's it — no database setup, no config files.

## Usage

1. Click `+` or press `N` to add a note
2. Set a **wake date** — the date the note becomes relevant (not a deadline)
3. Assign an **owner** and **group** (e.g. "Backend Team", "Sprint 7", "Customer X")
4. Optionally tag with free-form labels (e.g. `backend`, `monitoring`, `on-call`)
5. Click a card to edit or resolve it
6. Use **Archive** to view and restore resolved notes

## API

All endpoints return JSON.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notes` | Active notes sorted by wake date |
| POST | `/api/notes` | Create a note |
| GET | `/api/notes/resolved` | Archived notes |
| GET | `/api/notes/{id}` | Single note |
| PATCH | `/api/notes/{id}` | Update any field |
| DELETE | `/api/notes/{id}` | Permanently delete |
| POST | `/api/notes/{id}/resolve` | Archive a note |
| GET | `/api/groups` | All group names in use |
| GET | `/api/tags` | All tags in use |
| GET | `/api/export` | Full JSON backup |
| POST | `/api/import` | Restore from JSON |

## Deployment

Prikbord is a single Python file backend + one HTML file frontend. Designed to run on a small VPS.

```bash
# On your server
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 2345
```

Point your domain at it, optionally put it behind nginx with TLS.

## Wake-up Logic

Notes automatically change appearance based on days until their wake date:

| Days | State | Visual |
|------|-------|--------|
| > 30 | dormant | Dim, muted |
| 3–30 | approaching | Amber border glow |
| 0–7 | imminent | Red glow, elevated |
| < 0 | overdue | Pulsing red border |

## Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: SQLite (via aiosqlite, auto-created)
- **Frontend**: Vanilla HTML/CSS/JS — no build step, no dependencies
- **Tests**: pytest + httpx

## License

MIT — do whatever you want with it.
