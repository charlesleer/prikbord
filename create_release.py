#!/usr/bin/env python3
"""
create_release.py — Package prikbord as a distributable zip.

Usage:
    python create_release.py <version>
    python create_release.py 1.0.0

Output:
    prikbord-{version}.zip  — ready to distribute
"""

import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent
RELEASE_DIR = REPO_ROOT.parent / "releases"  # siblings to whitebored/

# Files that are essential to run the tool
ESSENTIAL_FILES = {
    REPO_ROOT / "main.py",
    REPO_ROOT / "database.py",
    REPO_ROOT / "models.py",
    REPO_ROOT / "requirements.txt",
    REPO_ROOT / "static" / "index.html",
}

README_CONTENT = """\
Prikbord — Smart Shared Sticky-Note Board

Setup:
    pip install -r requirements.txt

Run:
    uvicorn main:app --host 0.0.0.0 --port 2345 --reload

Open:
    http://localhost:2345

No database setup required — prikbord.db is created automatically on first run.
"""


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <version>")
        print(f"Example: python {sys.argv[0]} 1.0.0")
        sys.exit(1)

    version = sys.argv[1].strip()
    if not version:
        print("Error: version cannot be empty")
        sys.exit(1)

    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"Error: version must be in semver format (e.g. 1.0.0), got: {version}")
        sys.exit(1)

    # Verify all essential files exist
    missing = [f for f in ESSENTIAL_FILES if not f.exists()]
    if missing:
        print("Error: missing required files:")
        for f in missing:
            print(f"  {f.relative_to(REPO_ROOT)}")
        sys.exit(1)

    # Create staging directory
    stage_dir = RELEASE_DIR / f"prikbord-{version}"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)

    static_dir = stage_dir / "static"
    static_dir.mkdir(parents=True)

    # Copy essential files
    for src in ESSENTIAL_FILES:
        if src.name == "index.html":
            dst = static_dir / "index.html"
        else:
            dst = stage_dir / src.name
        shutil.copy2(src, dst)

    # Write README
    (stage_dir / "README.txt").write_text(README_CONTENT)

    # Create zip
    zip_path = RELEASE_DIR / f"prikbord-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in stage_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(stage_dir)
                zf.write(file, arcname)

    # Clean up staging directory
    shutil.rmtree(stage_dir)

    size_kb = zip_path.stat().st_size // 1024
    print(f"Created: {zip_path.name}  ({size_kb} KB)")
    print(f"  Contains: main.py, database.py, models.py, requirements.txt, static/index.html, README.txt")


if __name__ == "__main__":
    import re
    main()
