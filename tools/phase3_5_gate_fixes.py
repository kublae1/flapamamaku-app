from pathlib import Path
import re

path = Path("backend/app/phase45.py")
text = path.read_text(encoding="utf-8")
updated, count = re.subn(
    r'(@app\.delete\([^\n]+),\s*status_code=204\)',
    r'\1)',
    text,
)
if count:
    path.write_text(updated, encoding="utf-8")
    print(f"Removed invalid status_code=204 from {count} Phase 3-5 delete routes")
else:
    print("No invalid Phase 3-5 delete decorators remain")
