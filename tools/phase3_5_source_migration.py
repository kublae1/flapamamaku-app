from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing source anchor: {label}")
    return text.replace(old, new, 1)


# ---------- backend main ----------
path = Path("backend/app/main.py")
text = path.read_text(encoding="utf-8")
text = replace_once(text, 'API_VERSION = "0.8.56"', 'API_VERSION = "0.9.0"', "api version")
text = replace_once(text, 'CURRENT_SCHEMA_VERSION = 8', 'CURRENT_SCHEMA_VERSION = 10', "schema version")

text = replace_once(
    text,
    '''            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1
            """,
            (_token_hash(token), now),''',
    '''            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.instance_id = ?
              AND s.expires_at > ?
              AND u.active = 1
            """,
            (_token_hash(token), INSTANCE_ID, now),''',
    "tenant-bound current_user",
)
text = replace_once(
    text,
    'db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))',
    'db.execute("DELETE FROM sessions WHERE token_hash = ? AND instance_id = ?", (_token_hash(token), INSTANCE_ID))',
    "tenant-bound logout",
)
text = replace_once(
    text,
    '''        init_db()
        with connect() as db:
            db.execute("DELETE FROM sessions")''',
    '''        init_db()
        phase45_initializer = getattr(app.state, "phase45_initializer", None)
        if callable(phase45_initializer):
            phase45_initializer()
        with connect() as db:
            db.execute("DELETE FROM sessions")''',
    "restore phase45 migration",
)
text = replace_once(
    text,
    '''def get_content(
    section: str | None = None,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM content_items"''',
    '''def get_content(
    section: str | None = None,
    user: dict[str, Any] = Depends(current_user),
) -> list[dict[str, Any]]:
    if section in {"sujet", "archive"}:
        return []
    sql = "SELECT * FROM content_items WHERE section NOT IN ('sujet', 'archive')"''',
    "canonical sujet content read",
)
text = replace_once(
    text,
    '''    if section:
        _content_permission(section)
        sql += " WHERE section = ?"''',
    '''    if section:
        _content_permission(section)
        sql += " AND section = ?"''',
    "content section where clause",
)
text = replace_once(
    text,
    '''def post_content(
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)''',
    '''def post_content(
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    if payload.section in {"sujet", "archive"}:
        raise HTTPException(
            status_code=409,
            detail="Sujet und Archiv werden über das Jahres-Sujet-Modell verwaltet",
        )
    _require_content_permission(payload.section, user)''',
    "block legacy sujet create",
)
text = replace_once(
    text,
    '''def put_content(
    row_id: int,
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    _require_content_permission(payload.section, user)''',
    '''def put_content(
    row_id: int,
    payload: ContentPayload,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    if payload.section in {"sujet", "archive"}:
        raise HTTPException(
            status_code=409,
            detail="Sujet und Archiv werden über das Jahres-Sujet-Modell verwaltet",
        )
    _require_content_permission(payload.section, user)''',
    "block legacy sujet update",
)

# Remove the first of the duplicate member-order route definitions.
first = text.find('@app.put("/api/members/order")')
second = text.find('@app.put("/api/members/order")', first + 1) if first >= 0 else -1
if first >= 0 and second >= 0:
    text = text[:first] + text[second:]
elif first < 0:
    raise SystemExit("missing source anchor: member reorder route")

install = '''\n\n# Phase 4/5 extensions.\nfrom .phase45 import install_phase45\n\ninstall_phase45(\n    app,\n    connect=connect,\n    current_user=current_user,\n    require=require,\n    optimize_image=_optimize_image,\n    instance_id=INSTANCE_ID,\n    is_production=IS_PRODUCTION,\n)\n'''
if "install_phase45(" not in text:
    text = text.rstrip() + install + "\n"
path.write_text(text, encoding="utf-8")


# ---------- phase45 restore hook ----------
path = Path("backend/app/phase45.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    @app.on_event("startup")
    async def phase45_startup() -> None:
        init_phase45()''',
    '''    app.state.phase45_initializer = init_phase45

    @app.on_event("startup")
    async def phase45_startup() -> None:
        init_phase45()''',
    "phase45 initializer hook",
)
path.write_text(text, encoding="utf-8")


# ---------- Flutter API ----------
path = Path("lib/data/api_service.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''  Map<String, String> get authHeaders => {
        if (hasToken) 'Authorization': 'Bearer $_token',
      };''',
    '''  Map<String, String> get authHeaders => {
        if (expectedInstanceId.trim().isNotEmpty)
          'X-Club-Instance': expectedInstanceId.trim().toLowerCase(),
        if (hasToken) 'Authorization': 'Bearer $_token',
      };''',
    "mobile tenant header",
)
text = replace_once(
    text,
    "          headers: const {'Content-Type': 'application/json'},",
    "          headers: _jsonHeaders,",
    "login tenant header",
)
text = replace_once(
    text,
    "        .get(_uri('/api/app-config'))",
    "        .get(_uri('/api/app-config'), headers: authHeaders)",
    "app config tenant header",
)

start = text.index("  Future<List<ContentItem>> fetchContent({String? section}) async {")
end = text.index("  Future<ContentItem> saveContent(ContentItem item) async {", start)
replacement = '''  Future<List<ContentItem>> fetchSujets({String scope = 'all'}) async {
    final response = await http
        .get(
          _uri('/api/sujets?scope=${Uri.encodeQueryComponent(scope)}'),
          headers: authHeaders,
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values.map((value) {
      final json = _prepareContentJson(
        Map<String, dynamic>.from(value as Map<String, dynamic>),
      );
      return ContentItem.fromJson(json);
    }).toList();
  }

  Future<List<ContentItem>> fetchContent({String? section}) async {
    if (section == 'polls') return fetchPolls();
    if (section == 'sujet') return fetchSujets(scope: 'current');
    if (section == 'archive') return fetchSujets(scope: 'archive');

    final suffix = section == null || section.isEmpty
        ? ''
        : '?section=${Uri.encodeQueryComponent(section)}';
    final response = await http
        .get(_uri('/api/content$suffix'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    final generic = values
        .map((value) {
          final json = _prepareContentJson(
            Map<String, dynamic>.from(value as Map<String, dynamic>),
          );
          return ContentItem.fromJson(json);
        })
        .where((item) => item.section != 'polls' &&
            item.section != 'sujet' && item.section != 'archive')
        .toList();
    if (section != null) return generic;
    final sujets = await fetchSujets();
    return [...generic, ...sujets];
  }

'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")


# ---------- Flutter content model ----------
path = Path("lib/models/app_data.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''  final int? id;
  final String section;
  final String title;''',
    '''  final int? id;
  final String section;
  final bool annualSujet;
  final int? year;
  final bool isCurrent;
  final String title;''',
    "content annual fields",
)
text = replace_once(
    text,
    '''    this.id,
    required this.section,
    required this.title,''',
    '''    this.id,
    required this.section,
    this.annualSujet = false,
    this.year,
    this.isCurrent = false,
    required this.title,''',
    "content annual constructor",
)
text = replace_once(
    text,
    '''      id: json['id'] as int?,
      section: json['section']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
''',
    '''      id: json['id'] as int?,
      section: json['section']?.toString() ?? '',
      annualSujet: json['annual_sujet'] == true,
      year: json['year'] is int
          ? json['year'] as int
          : int.tryParse(json['year']?.toString() ?? ''),
      isCurrent: json['is_current'] == true,
      title: json['title']?.toString() ?? '',
''',
    "content annual parsing",
)
text = replace_once(
    text,
    '''        'id': id,
        'section': section,
        'title': title,''',
    '''        'id': id,
        'section': section,
        'annual_sujet': annualSujet,
        'year': year,
        'is_current': isCurrent,
        'title': title,''',
    "content annual cache",
)
path.write_text(text, encoding="utf-8")


# ---------- browser admin ----------
path = Path("backend/static/admin.html")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''let token = sessionStorage.getItem("flapamamaku_token") || "";
let apiVersion = "";''',
    '''let token = sessionStorage.getItem("flapamamaku_token") || "";
let apiVersion = "";
let clubInstanceId = "";''',
    "admin tenant state",
)
text = replace_once(
    text,
    '''  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {...options, headers: {...headers, ...(options.headers || {})}});''',
    '''  if (clubInstanceId) headers["X-Club-Instance"] = clubInstanceId;
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {...options, headers: {...headers, ...(options.headers || {})}});''',
    "admin tenant api header",
)
text = replace_once(
    text,
    '''    const health = await api("/api/health");
    apiVersion = health.version || "";
    const status = await api("/api/auth/status");''',
    '''    const health = await api("/api/health");
    apiVersion = health.version || "";
    clubInstanceId = String(health.instance_id || "").trim().toLowerCase();
    const status = await api("/api/auth/status");''',
    "admin tenant bootstrap",
)

select_end = '''            <option value="whatsapp">WhatsApp-Gruppe</option>
          </select>'''
annual_fields = select_end + '''
          <div id="sujet-meta-wrap" class="hidden">
            <label>Jahr</label>
            <input name="sujet_year" type="number" min="1900" max="2200" inputmode="numeric">
            <label style="display:flex;align-items:center;gap:8px">
              <input name="sujet_is_current" type="checkbox">
              Aktuelles Sujet (erscheint unter «Sujet»)
            </label>
            <p class="meta">Pro Jahr ist genau ein Sujet möglich. Ein aktuelles Sujet wird automatisch aus dem Archiv herausgenommen.</p>
          </div>'''
text = replace_once(text, select_end, annual_fields, "annual sujet admin fields")
text = replace_once(
    text,
    '''  document.getElementById("document-upload-wrap")
    .classList.toggle("hidden", section !== "documents");''',
    '''  const annualSujet = section === "sujet" || section === "archive";
  const sujetMeta = document.getElementById("sujet-meta-wrap");
  sujetMeta.classList.toggle("hidden", !annualSujet);
  form.elements.sujet_year.required = annualSujet;
  if (annualSujet && !form.elements.sujet_year.value) {
    form.elements.sujet_year.value = String(new Date().getFullYear() + (section === "sujet" ? 1 : 0));
    form.elements.sujet_is_current.checked = section === "sujet";
  }
  document.getElementById("document-upload-wrap")
    .classList.toggle("hidden", section !== "documents");''',
    "annual sujet form mode",
)
text = replace_once(
    text,
    '''async function loadContent() {
  const items = await api("/api/content");''',
    '''async function loadContent() {
  const [genericItems, annualSujets] = await Promise.all([
    api("/api/content"),
    api("/api/sujets"),
  ]);
  const items = [
    ...genericItems.filter(item => !["sujet", "archive"].includes(item.section)),
    ...annualSujets,
  ];''',
    "admin canonical sujet load",
)
text = replace_once(
    text,
    '''  const updated = await api(`/api/content/${item.id}/images/order`, {''',
    '''  const base = item?.annual_sujet ? `/api/sujets/${item.id}` : `/api/content/${item.id}`;
  const updated = await api(`${base}/images/order`, {''',
    "annual image order",
)
text = replace_once(
    text,
    '''      await api(`/api/content/${item.id}/images/${image.id}`, {method:"DELETE"});
      const refreshed = await api("/api/content");
      const updated = refreshed.find(entry => entry.id === item.id);''',
    '''      const base = item?.annual_sujet ? `/api/sujets/${item.id}` : `/api/content/${item.id}`;
      await api(`${base}/images/${image.id}`, {method:"DELETE"});
      const refreshed = item?.annual_sujet ? await api("/api/sujets") : await api("/api/content");
      const updated = refreshed.find(entry => entry.id === item.id);''',
    "annual image delete",
)
text = replace_once(
    text,
    '''  form.elements.poll_options.value = "";
  form.elements.poll_allow_suggestions.checked = false;''',
    '''  form.elements.poll_options.value = "";
  form.elements.poll_allow_suggestions.checked = false;
  form.elements.sujet_year.value = "";
  form.elements.sujet_is_current.checked = section === "sujet";''',
    "annual form reset",
)
text = replace_once(
    text,
    '''  form.elements.link_url.value = item.link_url || "";
  form.elements.poll_options.value = (item.poll_options || []).join("\\n");''',
    '''  form.elements.link_url.value = item.link_url || "";
  form.elements.sujet_year.value = item.year || "";
  form.elements.sujet_is_current.checked = item.is_current === true;
  form.elements.poll_options.value = (item.poll_options || []).join("\\n");''',
    "annual form edit",
)
text = replace_once(
    text,
    '''  const path = section === "polls"
    ? `/api/polls/${id}`
    : `/api/content/${id}`;''',
    '''  const path = section === "polls"
    ? `/api/polls/${id}`
    : (["sujet", "archive"].includes(section)
        ? `/api/sujets/${id}`
        : `/api/content/${id}`);''',
    "annual delete",
)
old_save = '''  const saved = section === "polls"
    ? await api(id ? `/api/polls/${id}` : "/api/polls", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(pollPayload),
      })
    : await api(id ? `/api/content/${id}` : "/api/content", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(contentPayload),
      });'''
new_save = '''  const isAnnualSujet = section === "sujet" || section === "archive";
  let saved;
  if (section === "polls") {
    saved = await api(id ? `/api/polls/${id}` : "/api/polls", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(pollPayload),
    });
  } else if (isAnnualSujet) {
    const year = Number(form.elements.sujet_year.value);
    if (!Number.isInteger(year) || year < 1900 || year > 2200) {
      alert("Bitte ein gültiges Sujet-Jahr erfassen.");
      return;
    }
    saved = await api(id ? `/api/sujets/${id}` : "/api/sujets", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify({
        year,
        title: contentPayload.title,
        text: contentPayload.text,
        is_current: form.elements.sujet_is_current.checked,
      }),
    });
  } else {
    saved = await api(id ? `/api/content/${id}` : "/api/content", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(contentPayload),
    });
  }'''
text = replace_once(text, old_save, new_save, "annual save")
text = replace_once(
    text,
    '''    if (id && form.elements.replace_images.checked) {
      await api(`/api/content/${saved.id}/images`, {method:"DELETE"});
    }
    const upload = new FormData();
    files.forEach(file => upload.append("images", file));
    await api(`/api/content/${saved.id}/images`, {
      method:"POST",
      body:upload,
    });''',
    '''    const mediaBase = isAnnualSujet
      ? `/api/sujets/${saved.id}`
      : `/api/content/${saved.id}`;
    if (id && form.elements.replace_images.checked) {
      const existing = saved.images || [];
      for (const image of existing) {
        await api(`${mediaBase}/images/${image.id}`, {method:"DELETE"});
      }
    }
    const upload = new FormData();
    files.forEach(file => upload.append("images", file));
    await api(`${mediaBase}/images`, {
      method:"POST",
      body:upload,
    });''',
    "annual image upload",
)
text = text.replace(
    'const headers = token ? {Authorization: `Bearer ${token}`} : {};',
    '''const headers = {
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      ...(clubInstanceId ? {"X-Club-Instance": clubInstanceId} : {}),
    };''',
)
text = text.replace(
    'headers: token ? {Authorization: `Bearer ${token}`} : {},',
    '''headers: {
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      ...(clubInstanceId ? {"X-Club-Instance": clubInstanceId} : {}),
    },''',
)
path.write_text(text, encoding="utf-8")


# ---------- version ----------
path = Path("pubspec.yaml")
text = path.read_text(encoding="utf-8")
text = re.sub(r"^version:\s*[^\n]+", "version: 0.9.0+36", text, count=1, flags=re.MULTILINE)
path.write_text(text, encoding="utf-8")

print("Phase 3-5 source migration applied")
