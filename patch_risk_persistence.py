
from pathlib import Path

path = Path("engines/paper_persistence.py")
source = path.read_text(encoding="utf-8")

start_marker = "                    int(\n                        bool(\n                            event.get("
end_marker = "                    ),"

start = source.find(start_marker)

if start == -1:
    raise SystemExit("STOP: original code block not found; file unchanged.")

end = source.find(end_marker, start)

if end == -1:
    raise SystemExit("STOP: end of code block not found; file unchanged.")

end += len(end_marker)

old_block = source[start:end]

if '"allowed"' not in old_block or "False" not in old_block:
    raise SystemExit("STOP: code does not match expected original; file unchanged.")

new_block = '''                    (
                        None
                        if event.get("allowed") is None
                        else int(bool(event.get("allowed")))
                    ),'''

print("Original block found:")
print(old_block)

confirm = input("Type PATCH to apply this change: ")

if confirm != "PATCH":
    raise SystemExit("Cancelled; file unchanged.")

backup = path.with_suffix(".py.bak")
if not backup.exists():
    backup.write_text(source, encoding="utf-8")

path.write_text(source[:start] + new_block + source[end:], encoding="utf-8")
print("Patch applied. Backup:", backup)
