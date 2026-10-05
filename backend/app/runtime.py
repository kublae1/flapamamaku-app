import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import main as main_app

app = main_app.app
INSTANCE_ID = main_app.INSTANCE_ID
DB_PATH = main_app.DB_PATH
PLATFORM_DB = Path(os.getenv("FLAPAMAMAKU_PLATFORM_DB", "/platform/platform.db"))
PUBLIC_URL = os.getenv("FLAPAMAMAKU_PUBLIC_URL", "").strip().rstrip("/")
RUNTIME_VERSION = os.getenv("FLAPAMAMAKU_API_VERSION", "0.9.2").strip() or "0.9.2"

# Keep the visible backend version aligned with the repaired Phase-9 runtime
# without rewriting historical migration code in app.main.
main_app.API_VERSION = RUNTIME_VERSION
app.version = RUNTIME_VERSION


def _club_name() -> str:
    try:
        db = sqlite3.connect(DB_PATH, timeout=2)
        try:
            row = db.execute("SELECT app_name FROM app_config WHERE id=1").fetchone()
        finally:
            db.close()
        if row and str(row[0] or "").strip():
            return str(row[0]).strip()
    except sqlite3.Error:
        pass
    return "FLAPAMAMAKU" if INSTANCE_ID == "flapamamaku" else INSTANCE_ID


def register_platform_club() -> bool:
    """Register this running club instance in the shared Phase-9 platform DB.

    Registration is intentionally idempotent. Existing billing, suspension and
    accounting values are never overwritten by a club runtime.
    """
    if not PLATFORM_DB.exists():
        return False
    try:
        db = sqlite3.connect(PLATFORM_DB, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='platform_clubs'"
            ).fetchone()
            if not table:
                return False
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            existing = db.execute(
                "SELECT id,name,api_base_url FROM platform_clubs WHERE instance_id=? COLLATE NOCASE",
                (INSTANCE_ID,),
            ).fetchone()
            if existing is None:
                db.execute(
                    """
                    INSERT INTO platform_clubs(
                      instance_id,name,api_base_url,billing_email,monthly_fee_cents,
                      currency,billing_day,due_days,auto_suspend_overdue,status,
                      suspension_reason,created_at,updated_at
                    ) VALUES (?,?,?,'',0,'CHF',1,30,0,'active','',?,?)
                    """,
                    (INSTANCE_ID, _club_name(), PUBLIC_URL, now, now),
                )
            else:
                name = str(existing["name"] or "").strip()
                url = str(existing["api_base_url"] or "").strip()
                db.execute(
                    """
                    UPDATE platform_clubs
                    SET name=?, api_base_url=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        _club_name() if not name or name == INSTANCE_ID else name,
                        PUBLIC_URL if PUBLIC_URL and not url else url,
                        now,
                        existing["id"],
                    ),
                )
            db.commit()
            return True
        finally:
            db.close()
    except sqlite3.Error:
        return False


async def _platform_registration_loop() -> None:
    for _ in range(120):
        if await asyncio.to_thread(register_platform_club):
            return
        await asyncio.sleep(2)


@app.on_event("startup")
async def register_with_platform() -> None:
    asyncio.create_task(_platform_registration_loop())


def platform_access_state():
    if not PLATFORM_DB.exists():
        return "active", ""
    try:
        db = sqlite3.connect(f"file:{PLATFORM_DB}?mode=ro", uri=True, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT status,suspension_reason FROM platform_clubs WHERE instance_id=? COLLATE NOCASE",
                (INSTANCE_ID,),
            ).fetchone()
        finally:
            db.close()
    except sqlite3.Error:
        return "active", ""
    if not row:
        return "active", ""
    return str(row["status"]), str(row["suspension_reason"] or "")


@app.get("/api/system/platform-clubs")
def platform_clubs_for_admin(
    _user: dict = Depends(main_app.require("can_manage_users")),
):
    """Return the Phase-9 club registry to an authenticated club administrator."""
    if not PLATFORM_DB.exists():
        return []
    try:
        db = sqlite3.connect(f"file:{PLATFORM_DB}?mode=ro", uri=True, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='platform_clubs'"
            ).fetchone()
            if not table:
                return []
            rows = db.execute(
                """
                SELECT id, instance_id, name, api_base_url, status
                FROM platform_clubs
                ORDER BY name COLLATE NOCASE ASC, instance_id ASC
                """
            ).fetchall()
        finally:
            db.close()
    except sqlite3.Error:
        return []
    return [dict(row) for row in rows]


def _admin_selector_injection() -> str:
    return r'''
<style>
#platform-club-switcher{display:none;margin:0 auto 18px;max-width:1480px;background:#191b1e;border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:14px 16px;box-shadow:0 10px 30px rgba(0,0,0,.18)}
#platform-club-switcher .row{display:flex;gap:10px;align-items:end;flex-wrap:wrap}#platform-club-switcher label{margin:0;min-width:260px;flex:1}#platform-club-switcher select{margin-top:6px}#platform-club-switcher button{border:0;border-radius:10px;padding:11px 16px;background:#8a101b;color:white;font-weight:800;cursor:pointer}#platform-club-switcher .meta{margin-top:8px}
</style>
<script>
(() => {
  let lastToken = '';
  let loading = false;
  const box = document.createElement('section');
  box.id = 'platform-club-switcher';
  box.innerHTML = '<div class="row"><label>Verein auswählen<select id="platform-club-select"><option value="">Verein auswählen …</option></select></label><button type="button" id="platform-club-open">Vereins-Admin öffnen</button></div><div class="meta" id="platform-club-info">Vereine werden geladen …</div>';
  const main = document.querySelector('main');
  if (main) main.insertBefore(box, main.firstChild);

  async function refreshClubSelector() {
    const currentToken = sessionStorage.getItem('flapamamaku_token') || '';
    if (!currentToken) {
      lastToken = '';
      box.style.display = 'none';
      return;
    }
    if (loading || currentToken === lastToken) return;
    loading = true;
    try {
      const response = await fetch('/api/system/platform-clubs', {
        headers: {Authorization: 'Bearer ' + currentToken},
        cache: 'no-store'
      });
      if (!response.ok) {
        box.style.display = 'none';
        return;
      }
      const clubs = await response.json();
      const select = document.getElementById('platform-club-select');
      select.innerHTML = '<option value="">Verein auswählen …</option>';
      for (const club of clubs) {
        const option = document.createElement('option');
        option.value = club.api_base_url || '';
        option.textContent = `${club.name || club.instance_id} (${club.instance_id})${club.status === 'suspended' ? ' – gesperrt' : ''}`;
        option.dataset.instanceId = club.instance_id || '';
        select.appendChild(option);
      }
      document.getElementById('platform-club-info').textContent = clubs.length
        ? `${clubs.length} Verein(e) verfügbar.`
        : 'Noch keine Vereine in der Plattform registriert.';
      box.style.display = 'block';
      lastToken = currentToken;
    } catch (_) {
      box.style.display = 'none';
    } finally {
      loading = false;
    }
  }

  document.getElementById('platform-club-open').addEventListener('click', () => {
    const select = document.getElementById('platform-club-select');
    const option = select.options[select.selectedIndex];
    if (!option || !select.value) return;
    const base = select.value.replace(/\/$/, '');
    window.location.href = base + '/admin';
  });

  refreshClubSelector();
  setInterval(refreshClubSelector, 1000);
})();
</script>
'''


@app.middleware("http")
async def platform_access_control(request: Request, call_next):
    path = request.url.path
    if path == "/api/health" or path.endswith("flapamamaku-icon.png"):
        return await call_next(request)
    status, reason = platform_access_state()
    if status != "suspended":
        if path in {"/admin", "/admin/"}:
            try:
                html = (main_app.STATIC_DIR / "admin.html").read_text(encoding="utf-8")
                html = html.replace("</body>", _admin_selector_injection() + "</body>")
                return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})
            except OSError:
                return await call_next(request)
        return await call_next(request)
    message = reason or "Dieser Verein ist durch die Plattformverwaltung vorübergehend gesperrt."
    if path.startswith("/api/"):
        return JSONResponse(status_code=423, content={"detail": message, "club_status": "suspended"})
    return HTMLResponse(
        status_code=423,
        content=(
            "<!doctype html><html><head><meta charset='utf-8'><title>Verein gesperrt</title>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
            "<body style='font-family:system-ui;margin:3rem;max-width:720px'>"
            "<h1>Zugriff vorübergehend gesperrt</h1><p>" + message + "</p></body></html>"
        ),
    )
