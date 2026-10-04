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
    '''            SELECT u.*\n            FROM sessions s\n            JOIN users u ON u.id = s.user_id\n            WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1\n            """,\n            (_token_hash(token), now),''',
    '''            SELECT u.*\n            FROM sessions s\n            JOIN users u ON u.id = s.user_id\n            WHERE s.token_hash = ?\n              AND s.instance_id = ?\n              AND s.expires_at > ?\n              AND u.active = 1\n            """,\n            (_token_hash(token), INSTANCE_ID, now),''',
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
    '''        init_db()\n        with connect() as db:\n            db.execute("DELETE FROM sessions")''',
    '''        init_db()\n        phase45_initializer = getattr(app.state, "phase45_initializer", None)\n        if callable(phase45_initializer):\n            phase45_initializer()\n        with connect() as db:\n            db.execute("DELETE FROM sessions")''',
    "restore phase45 migration",
)

text = replace_once(
    text,
    '''def get_content(\n    section: str | None = None,\n    user: dict[str, Any] = Depends(current_user),\n) -> list[dict[str, Any]]:\n    sql = "SELECT * FROM content_items"''',
    '''def get_content(\n    section: str | None = None,\n    user: dict[str, Any] = Depends(current_user),\n) -> list[dict[str, Any]]:\n    # Phase 4: Sujet/Archiv are served exclusively by /api/sujets.\n    if section in {"sujet", "archive"}:\n        return []\n    sql = "SELECT * FROM content_items WHERE section NOT IN ('sujet', 'archive')"''',
    "canonical sujet content read",
)
text = replace_once(
    text,
    '''    if section:\n        _content_permission(section)\n        sql += " WHERE section = ?"''',
    '''    if section:\n        _content_permission(section)\n        sql += " AND section = ?"''',
    "content section where clause",
)
text = replace_once(
    text,
    '''def post_content(\n    payload: ContentPayload,\n    user: dict[str, Any] = Depends(current_user),\n) -> dict[str, Any]:\n    _require_content_permission(payload.section, user)''',
    '''def post_content(\n    payload: ContentPayload,\n    user: dict[str, Any] = Depends(current_user),\n) -> dict[str, Any]:\n    if payload.section in {"sujet", "archive"}:\n        raise HTTPException(\n            status_code=409,\n            detail="Sujet und Archiv werden über das Jahres-Sujet-Modell verwaltet",\n        )\n    _require_content_permission(payload.section, user)''',
    "block legacy sujet create",
)
text = replace_once(
    text,
    '''def put_content(\n    row_id: int,\n    payload: ContentPayload,\n    user: dict[str, Any] = Depends(current_user),\n) -> dict[str, Any]:\n    _require_content_permission(payload.section, user)''',
    '''def put_content(\n    row_id: int,\n    payload: ContentPayload,\n    user: dict[str, Any] = Depends(current_user),\n) -> dict[str, Any]:\n    if payload.section in {"sujet", "archive"}:\n        raise HTTPException(\n            status_code=409,\n            detail="Sujet und Archiv werden über das Jahres-Sujet-Modell verwaltet",\n        )\n    _require_content_permission(payload.section, user)''',
    "block legacy sujet update",
)

# Remove the first of two duplicate member-order route definitions.
pattern = re.compile(
    r'''\n@app\.put\("/api/members/order"\)\ndef reorder_members\(\n    payload: ContentOrderPayload,\n    _: dict\[str, Any\] = Depends\(require\("can_members"\)\),\n\) -> list\[dict\[str, Any\]\]:\n    if not payload\.item_ids:\n        return \[\]\n\n    with connect\(\) as db:\n        rows = db\.execute\(\n            f"""\n            SELECT id\n            FROM members\n            WHERE id IN \(\{","\.join\("\?" for _ in payload\.item_ids\)\}\)\n            """,\n            payload\.item_ids,\n        \)\.fetchall\(\)\n\n        if len\(rows\) != len\(set\(payload\.item_ids\)\):\n            raise HTTPException\(status_code=422, detail="Mitgliederreihenfolge ist ungültig"\)\n\n        current_ids = \{\n            row\["id"\] for row in db\.execute\("SELECT id FROM members"\)\.fetchall\(\)\n        \}\n        if set\(payload\.item_ids\) != current_ids:\n            raise HTTPException\(\n                status_code=422,\n                detail="Mitgliederreihenfolge ist unvollständig",\n            \)\n\n        for position, member_id in enumerate\(payload\.item_ids, start=1\):\n            db\.execute\(\n                "UPDATE members SET sort_order = \? WHERE id = \?",\n                \(position, member_id\),\n            \)\n        db\.commit\(\)\n\n    return list_rows\("members"\)\n''',
    re.MULTILINE,
)
text, removed = pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit("could not remove duplicate reorder_members route")

install = '''\n\n# Phase 4/5 extensions are intentionally installed after the legacy routes so\n# migrations can reuse the established database/auth primitives without\n# duplicating infrastructure.\nfrom .phase45 import install_phase45\n\ninstall_phase45(\n    app,\n    connect=connect,\n    current_user=current_user,\n    require=require,\n    optimize_image=_optimize_image,\n    instance_id=INSTANCE_ID,\n    is_production=IS_PRODUCTION,\n)\n'''
if "install_phase45(" not in text:
    text = text.rstrip() + install + "\n"
path.write_text(text, encoding="utf-8")


# ---------- phase45 restore hook ----------
path = Path("backend/app/phase45.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    @app.on_event("startup")\n    async def phase45_startup() -> None:\n        init_phase45()''',
    '''    app.state.phase45_initializer = init_phase45\n\n    @app.on_event("startup")\n    async def phase45_startup() -> None:\n        init_phase45()''',
    "phase45 initializer hook",
)
path.write_text(text, encoding="utf-8")


# ---------- Flutter API ----------
path = Path("lib/data/api_service.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''  Map<String, String> get authHeaders => {\n        if (hasToken) 'Authorization': 'Bearer $_token',\n      };''',
    '''  Map<String, String> get authHeaders => {\n        if (expectedInstanceId.trim().isNotEmpty)\n          'X-Club-Instance': expectedInstanceId.trim().toLowerCase(),\n        if (hasToken) 'Authorization': 'Bearer $_token',\n      };''',
    "mobile tenant header",
)
text = replace_once(
    text,
    '''          headers: const {'Content-Type': 'application/json'},''',
    '''          headers: _jsonHeaders,''',
    "login tenant header",
)
text = replace_once(
    text,
    '''        .get(_uri('/api/app-config'))''',
    '''        .get(_uri('/api/app-config'), headers: authHeaders)''',
    "app config tenant header",
)

start = text.index("  Future<List<ContentItem>> fetchContent({String? section}) async {")
end = text.index("  Future<ContentItem> saveContent(ContentItem item) async {", start)
replacement = '''  Future<List<ContentItem>> fetchSujets({String scope = 'all'}) async {\n    final response = await http\n        .get(\n          _uri('/api/sujets?scope=${Uri.encodeQueryComponent(scope)}'),\n          headers: authHeaders,\n        )\n        .timeout(const Duration(seconds: 8));\n    _ensureSuccess(response);\n    final values = jsonDecode(response.body) as List<dynamic>;\n    return values.map((value) {\n      final json = _prepareContentJson(\n        Map<String, dynamic>.from(value as Map<String, dynamic>),\n      );\n      return ContentItem.fromJson(json);\n    }).toList();\n  }\n\n  Future<List<ContentItem>> fetchContent({String? section}) async {\n    if (section == 'polls') {\n      return fetchPolls();\n    }\n    if (section == 'sujet') {\n      return fetchSujets(scope: 'current');\n    }\n    if (section == 'archive') {\n      return fetchSujets(scope: 'archive');\n    }\n\n    final suffix = section == null || section.isEmpty\n        ? ''\n        : '?section=${Uri.encodeQueryComponent(section)}';\n    final response = await http\n        .get(_uri('/api/content$suffix'), headers: authHeaders)\n        .timeout(const Duration(seconds: 8));\n    _ensureSuccess(response);\n    final values = jsonDecode(response.body) as List<dynamic>;\n    final generic = values\n        .map((value) {\n          final json = _prepareContentJson(\n            Map<String, dynamic>.from(value as Map<String, dynamic>),\n          );\n          return ContentItem.fromJson(json);\n        })\n        .where((item) => item.section != 'polls' &&\n            item.section != 'sujet' && item.section != 'archive')\n        .toList();\n\n    if (section != null) return generic;\n    final sujets = await fetchSujets();\n    return [...generic, ...sujets];\n  }\n\n'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")


# ---------- Flutter content model ----------
path = Path("lib/models/app_data.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''  final int? id;\n  final String section;\n  final String title;''',
    '''  final int? id;\n  final String section;\n  final bool annualSujet;\n  final int? year;\n  final bool isCurrent;\n  final String title;''',
    "content annual fields",
)
text = replace_once(
    text,
    '''    this.id,\n    required this.section,\n    required this.title,''',
    '''    this.id,\n    required this.section,\n    this.annualSujet = false,\n    this.year,\n    this.isCurrent = false,\n    required this.title,''',
    "content annual constructor",
)
text = replace_once(
    text,
    '''      id: json['id'] as int?,\n      section: json['section']?.toString() ?? '',\n      title: json['title']?.toString() ?? '', ''',
    '''      id: json['id'] as int?,\n      section: json['section']?.toString() ?? '',\n      annualSujet: json['annual_sujet'] == true,\n      year: json['year'] is int\n          ? json['year'] as int\n          : int.tryParse(json['year']?.toString() ?? ''),\n      isCurrent: json['is_current'] == true,\n      title: json['title']?.toString() ?? '', ''',
    "content annual parsing",
)
text = replace_once(
    text,
    '''        'id': id,\n        'section': section,\n        'title': title,''',
    '''        'id': id,\n        'section': section,\n        'annual_sujet': annualSujet,\n        'year': year,\n        'is_current': isCurrent,\n        'title': title,''',
    "content annual cache",
)
path.write_text(text, encoding="utf-8")


# ---------- browser admin ----------
path = Path("backend/static/admin.html")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''let token = sessionStorage.getItem("flapamamaku_token") || "";\nlet apiVersion = "";''',
    '''let token = sessionStorage.getItem("flapamamaku_token") || "";\nlet apiVersion = "";\nlet clubInstanceId = "";''',
    "admin tenant state",
)
text = replace_once(
    text,
    '''  if (token) headers.Authorization = `Bearer ${token}`;\n  const response = await fetch(path, {...options, headers: {...headers, ...(options.headers || {})}});''',
    '''  if (clubInstanceId) headers["X-Club-Instance"] = clubInstanceId;\n  if (token) headers.Authorization = `Bearer ${token}`;\n  const response = await fetch(path, {...options, headers: {...headers, ...(options.headers || {})}});''',
    "admin tenant api header",
)
text = replace_once(
    text,
    '''    const health = await api("/api/health");\n    apiVersion = health.version || "";\n    const status = await api("/api/auth/status");''',
    '''    const health = await api("/api/health");\n    apiVersion = health.version || "";\n    clubInstanceId = String(health.instance_id || "").trim().toLowerCase();\n    const status = await api("/api/auth/status");''',
    "admin tenant bootstrap",
)

select_end = '''            <option value="whatsapp">WhatsApp-Gruppe</option>\n          </select>'''
annual_fields = select_end + '''\n          <div id="sujet-meta-wrap" class="hidden">\n            <label>Jahr</label>\n            <input name="sujet_year" type="number" min="1900" max="2200" inputmode="numeric">\n            <label style="display:flex;align-items:center;gap:8px">\n              <input name="sujet_is_current" type="checkbox">\n              Aktuelles Sujet (erscheint unter «Sujet»)\n            </label>\n            <p class="meta">Pro Jahr ist genau ein Sujet möglich. Ein aktuelles Sujet wird automatisch aus dem Archiv herausgenommen.</p>\n          </div>'''
text = replace_once(text, select_end, annual_fields, "annual sujet admin fields")

text = replace_once(
    text,
    '''  document.getElementById("document-upload-wrap")\n    .classList.toggle("hidden", section !== "documents");''',
    '''  const annualSujet = section === "sujet" || section === "archive";\n  const sujetMeta = document.getElementById("sujet-meta-wrap");\n  sujetMeta.classList.toggle("hidden", !annualSujet);\n  form.elements.sujet_year.required = annualSujet;\n  if (annualSujet && !form.elements.sujet_year.value) {\n    form.elements.sujet_year.value = String(new Date().getFullYear() + (section === "sujet" ? 1 : 0));\n    form.elements.sujet_is_current.checked = section === "sujet";\n  }\n  document.getElementById("document-upload-wrap")\n    .classList.toggle("hidden", section !== "documents");''',
    "annual sujet form mode",
)

text = replace_once(
    text,
    '''async function loadContent() {\n  const items = await api("/api/content");''',
    '''async function loadContent() {\n  const [genericItems, annualSujets] = await Promise.all([\n    api("/api/content"),\n    api("/api/sujets"),\n  ]);\n  const items = [\n    ...genericItems.filter(item => !["sujet", "archive"].includes(item.section)),\n    ...annualSujets,\n  ];''',
    "admin canonical sujet load",
)

text = replace_once(
    text,
    '''  const updated = await api(`/api/content/${item.id}/images/order`, {''',
    '''  const base = item?.annual_sujet ? `/api/sujets/${item.id}` : `/api/content/${item.id}`;\n  const updated = await api(`${base}/images/order`, {''',
    "annual image order",
)
text = replace_once(
    text,
    '''      await api(`/api/content/${item.id}/images/${image.id}`, {method:"DELETE"});\n      const refreshed = await api("/api/content");\n      const updated = refreshed.find(entry => entry.id === item.id);''',
    '''      const base = item?.annual_sujet ? `/api/sujets/${item.id}` : `/api/content/${item.id}`;\n      await api(`${base}/images/${image.id}`, {method:"DELETE"});\n      const refreshed = item?.annual_sujet ? await api("/api/sujets") : await api("/api/content");\n      const updated = refreshed.find(entry => entry.id === item.id);''',
    "annual image delete",
)
text = replace_once(
    text,
    '''  form.elements.poll_options.value = "";\n  form.elements.poll_allow_suggestions.checked = false;''',
    '''  form.elements.poll_options.value = "";\n  form.elements.poll_allow_suggestions.checked = false;\n  form.elements.sujet_year.value = "";\n  form.elements.sujet_is_current.checked = section === "sujet";''',
    "annual form reset",
)
text = replace_once(
    text,
    '''  form.elements.link_url.value = item.link_url || "";\n  form.elements.poll_options.value = (item.poll_options || []).join("\\n");''',
    '''  form.elements.link_url.value = item.link_url || "";\n  form.elements.sujet_year.value = item.year || "";\n  form.elements.sujet_is_current.checked = item.is_current === true;\n  form.elements.poll_options.value = (item.poll_options || []).join("\\n");''',
    "annual form edit",
)
text = replace_once(
    text,
    '''  const path = section === "polls"\n    ? `/api/polls/${id}`\n    : `/api/content/${id}`;''',
    '''  const path = section === "polls"\n    ? `/api/polls/${id}`\n    : (["sujet", "archive"].includes(section)\n        ? `/api/sujets/${id}`\n        : `/api/content/${id}`);''',
    "annual delete",
)

old_save = '''  const saved = section === "polls"\n    ? await api(id ? `/api/polls/${id}` : "/api/polls", {\n        method: id ? "PUT" : "POST",\n        body: JSON.stringify(pollPayload),\n      })\n    : await api(id ? `/api/content/${id}` : "/api/content", {\n        method: id ? "PUT" : "POST",\n        body: JSON.stringify(contentPayload),\n      });'''
new_save = '''  const isAnnualSujet = section === "sujet" || section === "archive";\n  let saved;\n  if (section === "polls") {\n    saved = await api(id ? `/api/polls/${id}` : "/api/polls", {\n      method: id ? "PUT" : "POST",\n      body: JSON.stringify(pollPayload),\n    });\n  } else if (isAnnualSujet) {\n    const year = Number(form.elements.sujet_year.value);\n    if (!Number.isInteger(year) || year < 1900 || year > 2200) {\n      alert("Bitte ein gültiges Sujet-Jahr erfassen.");\n      return;\n    }\n    saved = await api(id ? `/api/sujets/${id}` : "/api/sujets", {\n      method: id ? "PUT" : "POST",\n      body: JSON.stringify({\n        year,\n        title: contentPayload.title,\n        text: contentPayload.text,\n        is_current: form.elements.sujet_is_current.checked,\n      }),\n    });\n  } else {\n    saved = await api(id ? `/api/content/${id}` : "/api/content", {\n      method: id ? "PUT" : "POST",\n      body: JSON.stringify(contentPayload),\n    });\n  }'''
text = replace_once(text, old_save, new_save, "annual save")

text = replace_once(
    text,
    '''    if (id && form.elements.replace_images.checked) {\n      await api(`/api/content/${saved.id}/images`, {method:"DELETE"});\n    }\n    const upload = new FormData();\n    files.forEach(file => upload.append("images", file));\n    await api(`/api/content/${saved.id}/images`, {\n      method:"POST",\n      body:upload,\n    });''',
    '''    const mediaBase = isAnnualSujet\n      ? `/api/sujets/${saved.id}`\n      : `/api/content/${saved.id}`;\n    if (id && form.elements.replace_images.checked) {\n      const existing = saved.images || [];\n      for (const image of existing) {\n        await api(`${mediaBase}/images/${image.id}`, {method:"DELETE"});\n      }\n    }\n    const upload = new FormData();\n    files.forEach(file => upload.append("images", file));\n    await api(`${mediaBase}/images`, {\n      method:"POST",\n      body:upload,\n    });''',
    "annual image upload",
)

# Add tenant header to direct authenticated fetches used by previews/backups.
text = text.replace(
    '''const headers = token ? {Authorization: `Bearer ${token}`} : {};''',
    '''const headers = {\n      ...(token ? {Authorization: `Bearer ${token}`} : {}),\n      ...(clubInstanceId ? {"X-Club-Instance": clubInstanceId} : {}),\n    };''',
)
text = text.replace(
    '''headers: token ? {Authorization: `Bearer ${token}`} : {},''',
    '''headers: {\n      ...(token ? {Authorization: `Bearer ${token}`} : {}),\n      ...(clubInstanceId ? {"X-Club-Instance": clubInstanceId} : {}),\n    },''',
)
path.write_text(text, encoding="utf-8")


# ---------- version ----------
path = Path("pubspec.yaml")
text = path.read_text(encoding="utf-8")
text = re.sub(r"^version:\s*[^\n]+", "version: 0.9.0+36", text, count=1, flags=re.MULTILINE)
path.write_text(text, encoding="utf-8")

print("Phase 3-5 source migration applied")
