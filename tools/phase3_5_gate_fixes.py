from pathlib import Path

path = Path("backend/app/phase45.py")
text = path.read_text(encoding="utf-8")
old = '@app.delete("/api/sujets/{sujet_id}", status_code=204)'
new = '@app.delete("/api/sujets/{sujet_id}")'
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Phase 3-5 remaining backend gate fix applied")
elif new in text:
    print("Sujet delete route already fixed")
else:
    raise SystemExit("missing source anchor: sujet delete route")
