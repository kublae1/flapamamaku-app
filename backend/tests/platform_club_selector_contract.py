from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "static" / "platform.html").read_text(encoding="utf-8")
js = (ROOT / "static" / "platform.js").read_text(encoding="utf-8")

assert 'id="clubSelector"' in html, "Superuser club selector missing"
assert 'id="openClubAdmin"' in html, "Open club admin action missing"
assert "renderClubSelector" in js, "Club selector is not populated"
assert "/api/platform/clubs" in js, "Club selector must use platform club registry"
assert "clubAdminUrl" in js and "+'/admin'" in js, "Club admin routing missing"
assert 'data-open=' in js, "Club table needs direct open action"

print("platform club selector contract: ok")
