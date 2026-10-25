from pathlib import Path

path = Path("engines/paper_persistence.py")
source = path.read_text(encoding="utf-8")

old_import = "import sqlite3\n"
new_import = "import sqlite3\nfrom contextlib import closing\n"
old_context = "with self._connect() as connection:"
new_context = "with closing(self._connect()) as connection, connection:"

if "from contextlib import closing" in source:
    raise SystemExit("ABORT: closing import already exists; no changes made.")

if source.count(old_import) != 1:
    raise SystemExit("ABORT: expected one sqlite3 import; no changes made.")

count = source.count(old_context)
if count != 14:
    raise SystemExit(
        f"ABORT: expected 14 connection blocks, found {count}; no changes made."
    )

updated = source.replace(old_import, new_import, 1)
updated = updated.replace(old_context, new_context)

if updated.count(new_context) != 14:
    raise SystemExit("ABORT: replacement verification failed; no changes made.")

path.write_text(updated, encoding="utf-8")
print(f"PASS: added closing import and updated {count} connection blocks.")