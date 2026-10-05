from pathlib import Path

path = Path("backend/app/main.py")
text = path.read_text(encoding="utf-8")
route = '''@app.post("/api/members")
def post_members(
    payload: MemberPayload,
    _: dict[str, object] = Depends(require("can_members")),
) -> dict[str, object]:
    return create_row("members", payload)


'''
anchor = '''@app.put("/api/members/order")
def reorder_members(
'''
if '@app.post("/api/members")' not in text:
    if anchor not in text:
        raise SystemExit("missing source anchor: members order route")
    text = text.replace(anchor, route + anchor, 1)
    path.write_text(text, encoding="utf-8")
    print("Restored POST /api/members endpoint")
else:
    print("POST /api/members endpoint already present")
