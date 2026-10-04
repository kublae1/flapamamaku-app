from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing source anchor: {label}")
    return text.replace(old, new, 1)


# ---------------- backend main.py ----------------
path = Path("backend/app/main.py")
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''class EventPayload(BaseModel):
    event_date: str = ""
    day: str
    month: str
    title: str = Field(min_length=1, max_length=200)
    location: str = ""
    time: str = ""
''',
    '''class EventPayload(BaseModel):
    event_date: str = ""
    day: str
    month: str
    title: str = Field(min_length=1, max_length=200)
    location: str = ""
    time: str = ""
    end_time: str = ""
    meeting_point: str = ""
    description: str = ""
    responsible: str = ""
    registration_deadline: str = ""
    registration_enabled: bool = True
    document_url: str = ""
''',
    "event payload fields",
)

text = replace_once(
    text,
    '''            location TEXT NOT NULL DEFAULT '',
            time TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
''',
    '''            location TEXT NOT NULL DEFAULT '',
            time TEXT NOT NULL DEFAULT '',
            end_time TEXT NOT NULL DEFAULT '',
            meeting_point TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            responsible TEXT NOT NULL DEFAULT '',
            registration_deadline TEXT NOT NULL DEFAULT '',
            registration_enabled INTEGER NOT NULL DEFAULT 1,
            document_url TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
''',
    "event schema fields",
)

# Extend existing installations safely in init_db next to the existing event migration.
anchor = '''        _ensure_column(db, "events", "event_date", "TEXT NOT NULL DEFAULT ''")
'''
addition = anchor + '''        for column, definition in {
            "end_time": "TEXT NOT NULL DEFAULT ''",
            "meeting_point": "TEXT NOT NULL DEFAULT ''",
            "description": "TEXT NOT NULL DEFAULT ''",
            "responsible": "TEXT NOT NULL DEFAULT ''",
            "registration_deadline": "TEXT NOT NULL DEFAULT ''",
            "registration_enabled": "INTEGER NOT NULL DEFAULT 1",
            "document_url": "TEXT NOT NULL DEFAULT ''",
        }.items():
            _ensure_column(db, "events", column, definition)
'''
text = replace_once(text, anchor, addition, "event additive migration")

# Registration must respect disabled/deadline.
old = '''    with connect() as db:
        event = db.execute("SELECT id FROM events WHERE id = ?", (row_id,)).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        db.execute(
            """
            INSERT OR IGNORE INTO event_registrations (event_id, user_id, created_at)
'''
new = '''    with connect() as db:
        event = db.execute(
            "SELECT id, registration_enabled, registration_deadline FROM events WHERE id = ?",
            (row_id,),
        ).fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Termin nicht gefunden")
        if not bool(event["registration_enabled"]):
            raise HTTPException(status_code=409, detail="Für diesen Termin ist keine Anmeldung möglich")
        deadline = str(event["registration_deadline"] or "").strip()
        if deadline:
            try:
                deadline_value = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                if deadline_value.tzinfo is None:
                    deadline_value = deadline_value.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > deadline_value.astimezone(timezone.utc):
                    raise HTTPException(status_code=409, detail="Der Anmeldeschluss ist abgelaufen")
            except ValueError:
                pass
        db.execute(
            """
            INSERT OR IGNORE INTO event_registrations (event_id, user_id, created_at)
'''
text = replace_once(text, old, new, "registration guard")

path.write_text(text, encoding="utf-8")


# ---------------- backend phase45.py ----------------
path = Path("backend/app/phase45.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''class SujetPayload(BaseModel):
    year: int = Field(ge=1900, le=2200)
    title: str = Field(min_length=1, max_length=200)
    text: str = ""
    is_current: bool = False
''',
    '''class SujetPayload(BaseModel):
    year: int = Field(ge=1900, le=2200)
    title: str = Field(min_length=1, max_length=200)
    motto: str = Field(default="", max_length=300)
    text: str = ""
    is_current: bool = False
''',
    "sujet payload motto",
)

text = replace_once(
    text,
    '''                    title TEXT NOT NULL,
                    text TEXT NOT NULL DEFAULT '',
                    is_current INTEGER NOT NULL DEFAULT 0,
''',
    '''                    title TEXT NOT NULL,
                    motto TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL DEFAULT '',
                    logo_data BLOB,
                    logo_mime TEXT NOT NULL DEFAULT '',
                    is_current INTEGER NOT NULL DEFAULT 0,
''',
    "sujet schema motto logo",
)

# Ensure new columns for already-created annual_sujets and add club_id markers to core tables.
anchor = '''            ensure_column(
                db,
                "sessions",
                "instance_id",
                f"TEXT NOT NULL DEFAULT '{instance_id}'",
            )
'''
addition = '''            ensure_column(db, "annual_sujets", "motto", "TEXT NOT NULL DEFAULT ''")
            ensure_column(db, "annual_sujets", "logo_data", "BLOB")
            ensure_column(db, "annual_sujets", "logo_mime", "TEXT NOT NULL DEFAULT ''")

            tenant_tables = [
                "news", "events", "members", "member_filters", "content_items",
                "content_images", "event_registrations", "users", "sessions",
                "push_tokens", "annual_sujets", "annual_sujet_images",
            ]
            for table in tenant_tables:
                exists = db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                    (table,),
                ).fetchone()
                if exists is None:
                    continue
                ensure_column(
                    db,
                    table,
                    "club_id",
                    f"TEXT NOT NULL DEFAULT '{instance_id}'",
                )
                db.execute(
                    f"UPDATE {table} SET club_id = ? WHERE club_id = '' OR club_id IS NULL",
                    (instance_id,),
                )
                db.execute(
                    f"CREATE INDEX IF NOT EXISTS {table}_club_id_idx ON {table}(club_id)"
                )
                safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", table)
                db.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {safe_name}_club_guard_insert
                    BEFORE INSERT ON {table}
                    WHEN NEW.club_id <> '{instance_id}'
                    BEGIN
                      SELECT RAISE(ABORT, 'wrong club_id');
                    END
                    """
                )
                db.execute(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {safe_name}_club_guard_update
                    BEFORE UPDATE OF club_id ON {table}
                    WHEN NEW.club_id <> '{instance_id}'
                    BEGIN
                      SELECT RAISE(ABORT, 'wrong club_id');
                    END
                    """
                )

''' + anchor
text = replace_once(text, anchor, addition, "tenant club id hardening")

text = replace_once(
    text,
    '''            "title": str(row["title"] or ""),
            "text": str(row["text"] or ""),
''',
    '''            "title": str(row["title"] or ""),
            "motto": str(row["motto"] or ""),
            "text": str(row["text"] or ""),
            "logo_url": f"/api/sujets/{row['id']}/logo" if row["logo_data"] else "",
''',
    "serialize sujet motto logo",
)

text = replace_once(
    text,
    '''                        INSERT INTO annual_sujets (
                            year, title, text, is_current, sort_order,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
''',
    '''                        INSERT INTO annual_sujets (
                            year, title, motto, text, is_current, sort_order,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''',
    "insert sujet columns",
)
text = replace_once(
    text,
    '''                            payload.year,
                            payload.title.strip(),
                            payload.text.strip(),
                            1 if payload.is_current else 0,
                            next_order,
                            now,
                            now,
''',
    '''                            payload.year,
                            payload.title.strip(),
                            payload.motto.strip(),
                            payload.text.strip(),
                            1 if payload.is_current else 0,
                            next_order,
                            now,
                            now,
''',
    "insert sujet values",
)
text = replace_once(
    text,
    '''                        UPDATE annual_sujets
                        SET year = ?, title = ?, text = ?, is_current = ?, updated_at = ?
                        WHERE id = ?
''',
    '''                        UPDATE annual_sujets
                        SET year = ?, title = ?, motto = ?, text = ?, is_current = ?, updated_at = ?
                        WHERE id = ?
''',
    "update sujet columns",
)
text = replace_once(
    text,
    '''                            payload.year,
                            payload.title.strip(),
                            payload.text.strip(),
                            1 if payload.is_current else 0,
                            now,
                            sujet_id,
''',
    '''                            payload.year,
                            payload.title.strip(),
                            payload.motto.strip(),
                            payload.text.strip(),
                            1 if payload.is_current else 0,
                            now,
                            sujet_id,
''',
    "update sujet values",
)

# Add logo upload/read endpoints before delete sujet route.
marker = '''    @app.delete("/api/sujets/{sujet_id}", status_code=204)
'''
logo_routes = '''    @app.post("/api/sujets/{sujet_id}/logo")
    async def upload_sujet_logo(
        sujet_id: int,
        logo: UploadFile = File(...),
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> dict[str, Any]:
        raw = await logo.read()
        if not raw:
            raise HTTPException(status_code=422, detail="Leere Logo-Datei")
        optimized, mime = optimize_image(raw, logo.content_type or "image/jpeg")
        with connect() as db:
            cursor = db.execute(
                "UPDATE annual_sujets SET logo_data = ?, logo_mime = ?, updated_at = ? WHERE id = ?",
                (optimized, mime, datetime.now(timezone.utc).isoformat(), sujet_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()
            row = db.execute("SELECT * FROM annual_sujets WHERE id = ?", (sujet_id,)).fetchone()
        return serialize_sujet(row)

    @app.delete("/api/sujets/{sujet_id}/logo", status_code=204)
    def delete_sujet_logo(
        sujet_id: int,
        _: dict[str, Any] = Depends(require("can_photos")),
    ) -> None:
        with connect() as db:
            cursor = db.execute(
                "UPDATE annual_sujets SET logo_data = NULL, logo_mime = '', updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), sujet_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Sujet nicht gefunden")
            db.commit()

    @app.get("/api/sujets/{sujet_id}/logo")
    def get_sujet_logo(
        sujet_id: int,
        _: dict[str, Any] = Depends(current_user),
    ) -> Response:
        with connect() as db:
            row = db.execute(
                "SELECT logo_data, logo_mime FROM annual_sujets WHERE id = ?",
                (sujet_id,),
            ).fetchone()
        if row is None or not row["logo_data"]:
            raise HTTPException(status_code=404, detail="Sujet-Logo nicht gefunden")
        return Response(content=row["logo_data"], media_type=row["logo_mime"] or "image/jpeg")

''' + marker
text = replace_once(text, marker, logo_routes, "sujet logo routes")

path.write_text(text, encoding="utf-8")


# ---------------- Flutter model ----------------
path = Path("lib/models/app_data.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''  final bool isCurrent;
  final String title;
''',
    '''  final bool isCurrent;
  final String motto;
  final String logoUrl;
  final String title;
''',
    "content motto logo fields",
)
text = replace_once(
    text,
    '''    this.isCurrent = false,
    required this.title,
''',
    '''    this.isCurrent = false,
    this.motto = '',
    this.logoUrl = '',
    required this.title,
''',
    "content motto logo constructor",
)
text = replace_once(
    text,
    '''      isCurrent: json['is_current'] == true,
      title: json['title']?.toString() ?? '',
''',
    '''      isCurrent: json['is_current'] == true,
      motto: json['motto']?.toString() ?? '',
      logoUrl: json['logo_url']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
''',
    "content motto logo parsing",
)
text = replace_once(
    text,
    '''        'is_current': isCurrent,
        'title': title,
''',
    '''        'is_current': isCurrent,
        'motto': motto,
        'logo_url': logoUrl,
        'title': title,
''',
    "content motto logo cache",
)

# Expand EventItem.
text = replace_once(
    text,
    '''  final String time;
  final int registrationCount;
''',
    '''  final String time;
  final String endTime;
  final String meetingPoint;
  final String description;
  final String responsible;
  final String registrationDeadline;
  final bool registrationEnabled;
  final String documentUrl;
  final int registrationCount;
''',
    "event model fields",
)
text = replace_once(
    text,
    '''    this.eventDate = '',
    this.registrationCount = 0,
''',
    '''    this.eventDate = '',
    this.endTime = '',
    this.meetingPoint = '',
    this.description = '',
    this.responsible = '',
    this.registrationDeadline = '',
    this.registrationEnabled = true,
    this.documentUrl = '',
    this.registrationCount = 0,
''',
    "event model constructor",
)
text = replace_once(
    text,
    '''      eventDate: json['event_date']?.toString() ?? '',
      registrationCount: json['registration_count'] as int? ?? 0,
''',
    '''      eventDate: json['event_date']?.toString() ?? '',
      endTime: json['end_time']?.toString() ?? '',
      meetingPoint: json['meeting_point']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      responsible: json['responsible']?.toString() ?? '',
      registrationDeadline: json['registration_deadline']?.toString() ?? '',
      registrationEnabled: json['registration_enabled'] != false && json['registration_enabled'] != 0,
      documentUrl: json['document_url']?.toString() ?? '',
      registrationCount: json['registration_count'] as int? ?? 0,
''',
    "event model parsing",
)
text = replace_once(
    text,
    '''        'time': time,
        'registration_count': registrationCount,
''',
    '''        'time': time,
        'end_time': endTime,
        'meeting_point': meetingPoint,
        'description': description,
        'responsible': responsible,
        'registration_deadline': registrationDeadline,
        'registration_enabled': registrationEnabled,
        'document_url': documentUrl,
        'registration_count': registrationCount,
''',
    "event model cache",
)
path.write_text(text, encoding="utf-8")


# ---------------- Flutter API ----------------
path = Path("lib/data/api_service.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    final imageUrl = json['image_url']?.toString() ?? '';
    json['image_url'] = absolute(imageUrl);

    final documentUrl = json['document_url']?.toString() ?? '';
''',
    '''    final imageUrl = json['image_url']?.toString() ?? '';
    json['image_url'] = absolute(imageUrl);

    final logoUrl = json['logo_url']?.toString() ?? '';
    json['logo_url'] = absolute(logoUrl);

    final documentUrl = json['document_url']?.toString() ?? '';
''',
    "prepare logo url",
)
text = replace_once(
    text,
    '''      'location': item.location,
      'time': item.time,
    });
''',
    '''      'location': item.location,
      'time': item.time,
      'end_time': item.endTime,
      'meeting_point': item.meetingPoint,
      'description': item.description,
      'responsible': item.responsible,
      'registration_deadline': item.registrationDeadline,
      'registration_enabled': item.registrationEnabled,
      'document_url': item.documentUrl,
    });
''',
    "event api save fields",
)
path.write_text(text, encoding="utf-8")


# ---------------- Flutter admin event UI ----------------
path = Path("lib/screens/admin_screen.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''    final location = TextEditingController(text: existing?.location ?? '');
    final time = TextEditingController(text: existing?.time ?? '');
''',
    '''    final location = TextEditingController(text: existing?.location ?? '');
    final time = TextEditingController(text: existing?.time ?? '');
    final endTime = TextEditingController(text: existing?.endTime ?? '');
    final meetingPoint = TextEditingController(text: existing?.meetingPoint ?? '');
    final description = TextEditingController(text: existing?.description ?? '');
    final responsible = TextEditingController(text: existing?.responsible ?? '');
    final registrationDeadline = TextEditingController(text: existing?.registrationDeadline ?? '');
    final documentUrl = TextEditingController(text: existing?.documentUrl ?? '');
    var registrationEnabled = existing?.registrationEnabled ?? true;
''',
    "mobile admin event controllers",
)
text = replace_once(
    text,
    '''      builder: (dialogContext) => AlertDialog(
        title: Text(index == null ? 'Termin erfassen' : 'Termin bearbeiten'),
        content: SingleChildScrollView(
          child: Column(
''',
    '''      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
        title: Text(index == null ? 'Termin erfassen' : 'Termin bearbeiten'),
        content: SingleChildScrollView(
          child: Column(
''',
    "event dialog stateful",
)
text = replace_once(
    text,
    '''              TextField(
                controller: time,
                decoration: const InputDecoration(labelText: 'Zeit'),
              ),
''',
    '''              TextField(
                controller: time,
                decoration: const InputDecoration(labelText: 'Beginn'),
              ),
              TextField(
                controller: endTime,
                decoration: const InputDecoration(labelText: 'Ende (optional)'),
              ),
              TextField(
                controller: meetingPoint,
                decoration: const InputDecoration(labelText: 'Treffpunkt'),
              ),
              TextField(
                controller: responsible,
                decoration: const InputDecoration(labelText: 'Verantwortliche Person'),
              ),
              TextField(
                controller: registrationDeadline,
                decoration: const InputDecoration(
                  labelText: 'Anmeldeschluss',
                  hintText: 'YYYY-MM-DDTHH:MM:SS',
                ),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Anmeldung möglich'),
                value: registrationEnabled,
                onChanged: (value) => setDialogState(() => registrationEnabled = value),
              ),
              TextField(
                controller: description,
                minLines: 3,
                maxLines: 6,
                decoration: const InputDecoration(labelText: 'Beschreibung'),
              ),
              TextField(
                controller: documentUrl,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(labelText: 'Dokument-Link'),
              ),
''',
    "mobile admin event fields",
)
text = replace_once(
    text,
    '''        ],
      ),
    );

    if (save != true) return;
    final parsedDate = DateTime.tryParse(eventDate.text.trim());
''',
    '''        ],
      ),
      ),
    );

    if (save != true) return;
    final parsedDate = DateTime.tryParse(eventDate.text.trim());
''',
    "event dialog close stateful",
)
text = replace_once(
    text,
    '''      id: existing?.id,
      eventDate: eventDate.text.trim(),
    );
''',
    '''      id: existing?.id,
      eventDate: eventDate.text.trim(),
      endTime: endTime.text.trim(),
      meetingPoint: meetingPoint.text.trim(),
      description: description.text.trim(),
      responsible: responsible.text.trim(),
      registrationDeadline: registrationDeadline.text.trim(),
      registrationEnabled: registrationEnabled,
      documentUrl: documentUrl.text.trim(),
    );
''',
    "mobile admin event item",
)
path.write_text(text, encoding="utf-8")


# ---------------- Event detail UI + WhatsApp ----------------
path = Path("lib/screens/content_detail_screens.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''  Future<void> _message(BuildContext context) async {
    final number = member.phoneMobile.trim();
    if (number.isNotEmpty) {
      await _launch(context, Uri(scheme: 'sms', path: number));
    }
  }
''',
    '''  Future<void> _message(BuildContext context) async {
    final number = member.phoneMobile.replaceAll(RegExp(r'[^0-9+]'), '');
    if (number.isEmpty) return;
    final normalized = number.startsWith('+') ? number.substring(1) : number;
    await _launch(context, Uri.parse('https://wa.me/$normalized'));
  }
''',
    "member whatsapp action",
)
text = text.replace("label: 'Nachricht',", "label: 'WhatsApp',", 1)

# Disable registration button if configured off and show extra event fields.
text = replace_once(
    text,
    '''                        onPressed: _register,
                        icon: Icon(
''',
    '''                        onPressed: event.registrationEnabled ? _register : null,
                        icon: Icon(
''',
    "event registration enable",
)
text = replace_once(
    text,
    '''                      _DarkInfoRow(
                        icon: Icons.location_on_outlined,
                        text: event.location,
                      ),
''',
    '''                      _DarkInfoRow(
                        icon: Icons.location_on_outlined,
                        text: event.location,
                      ),
                      if (event.endTime.isNotEmpty) ...[
                        const _DarkDivider(),
                        _DarkInfoRow(icon: Icons.schedule_rounded, text: 'Ende: ${event.endTime}'),
                      ],
                      if (event.meetingPoint.isNotEmpty) ...[
                        const _DarkDivider(),
                        _DarkInfoRow(icon: Icons.place_outlined, text: 'Treffpunkt: ${event.meetingPoint}'),
                      ],
                      if (event.responsible.isNotEmpty) ...[
                        const _DarkDivider(),
                        _DarkInfoRow(icon: Icons.person_outline, text: 'Verantwortlich: ${event.responsible}'),
                      ],
                      if (event.registrationDeadline.isNotEmpty) ...[
                        const _DarkDivider(),
                        _DarkInfoRow(icon: Icons.timer_outlined, text: 'Anmeldeschluss: ${event.registrationDeadline}'),
                      ],
''',
    "event detail extra rows",
)
text = replace_once(
    text,
    '''                const SizedBox(height: 16),
                Row(
''',
    '''                if (event.description.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _DarkPanel(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(event.description, style: const TextStyle(color: Colors.white70, height: 1.5)),
                    ),
                  ),
                ],
                if (event.location.isNotEmpty || event.documentUrl.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 8,
                    alignment: WrapAlignment.center,
                    children: [
                      if (event.location.isNotEmpty)
                        OutlinedButton.icon(
                          onPressed: () => _launch(
                            context,
                            Uri.https('www.google.com', '/maps/search/', {'api': '1', 'query': event.location}),
                          ),
                          icon: const Icon(Icons.map_outlined),
                          label: const Text('Karte'),
                        ),
                      if (event.documentUrl.isNotEmpty)
                        OutlinedButton.icon(
                          onPressed: () {
                            final uri = Uri.tryParse(event.documentUrl);
                            if (uri != null) _launch(context, uri);
                          },
                          icon: const Icon(Icons.description_outlined),
                          label: const Text('Dokument'),
                        ),
                    ],
                  ),
                ],
                const SizedBox(height: 16),
                Row(
''',
    "event description map doc",
)
path.write_text(text, encoding="utf-8")


# ---------------- Year motto UI ----------------
path = Path("lib/screens/year_motto_screen.dart")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''                    child: Column(
                      children: [
                        if (images[_page].item.title.trim().isNotEmpty)
''',
    '''                    child: Column(
                      children: [
                        if (images[_page].item.logoUrl.trim().isNotEmpty) ...[
                          OfflineNetworkImage(
                            images[_page].item.logoUrl,
                            headers: store.api.authHeaders,
                            height: 110,
                            fit: BoxFit.contain,
                          ),
                          const SizedBox(height: 14),
                        ],
                        if (images[_page].item.title.trim().isNotEmpty)
''',
    "year motto logo",
)
text = replace_once(
    text,
    '''                        if (images[_page].item.text.trim().isNotEmpty) ...[
''',
    '''                        if (images[_page].item.motto.trim().isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            images[_page].item.motto.trim(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: FlapBrand.gold,
                              fontSize: 18,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ],
                        if (images[_page].item.text.trim().isNotEmpty) ...[
''',
    "year motto motto text",
)
path.write_text(text, encoding="utf-8")


# ---------------- PC admin ----------------
path = Path("backend/static/admin.html")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''          <label>Ort</label><input name="location">
          <label>Zeit</label><input name="time">
''',
    '''          <label>Ort</label><input name="location">
          <label>Beginn</label><input name="time">
          <label>Ende (optional)</label><input name="end_time">
          <label>Treffpunkt</label><input name="meeting_point">
          <label>Beschreibung</label><textarea name="description"></textarea>
          <label>Verantwortliche Person</label><input name="responsible">
          <label>Anmeldeschluss</label><input name="registration_deadline" type="datetime-local">
          <label style="display:flex;gap:8px;align-items:center"><input name="registration_enabled" type="checkbox" checked> Anmeldung möglich</label>
          <label>Dokument-Link</label><input name="document_url" type="url" placeholder="https://...">
''',
    "pc admin event fields",
)
text = replace_once(
    text,
    '''  events: ["event_date", "day", "month", "title", "location", "time"],
''',
    '''  events: ["event_date", "day", "month", "title", "location", "time", "end_time", "meeting_point", "description", "responsible", "registration_deadline", "document_url"],
''',
    "pc event resources",
)
text = replace_once(
    text,
    '''  resources[resource].forEach(key => data[key] = form.elements[key].value.trim());
  if (resource === "members") {
''',
    '''  resources[resource].forEach(key => data[key] = form.elements[key].value.trim());
  if (resource === "events") {
    data.registration_enabled = form.elements.registration_enabled.checked;
  }
  if (resource === "members") {
''',
    "pc event checkbox",
)
# edit function checkbox restoration anchor around generic edit
text = replace_once(
    text,
    '''    form.elements[key].value = item[key] || "";
  });

  if (resource === "members") {
''',
    '''    form.elements[key].value = item[key] || "";
  });

  if (resource === "events") {
    form.elements.registration_enabled.checked = item.registration_enabled !== false && item.registration_enabled !== 0;
  }

  if (resource === "members") {
''',
    "pc edit event checkbox",
)

# Annual sujet fields: motto and logo upload.
text = replace_once(
    text,
    '''            <label>Jahr</label>
            <input name="sujet_year" type="number" min="1900" max="2200" inputmode="numeric">
''',
    '''            <label>Jahr</label>
            <input name="sujet_year" type="number" min="1900" max="2200" inputmode="numeric">
            <label>Motto</label>
            <input name="sujet_motto" maxlength="300" placeholder="Jahresmotto">
            <label>Logo</label>
            <input name="sujet_logo_file" type="file" accept="image/*">
            <p id="sujet-logo-current" class="meta"></p>
''',
    "pc sujet motto logo fields",
)
text = replace_once(
    text,
    '''  form.elements.sujet_year.value = "";
  form.elements.sujet_is_current.checked = section === "sujet";
''',
    '''  form.elements.sujet_year.value = "";
  form.elements.sujet_motto.value = "";
  form.elements.sujet_logo_file.value = "";
  document.getElementById("sujet-logo-current").textContent = "";
  form.elements.sujet_is_current.checked = section === "sujet";
''',
    "pc sujet reset motto logo",
)
text = replace_once(
    text,
    '''  form.elements.sujet_year.value = item.year || "";
  form.elements.sujet_is_current.checked = item.is_current === true;
''',
    '''  form.elements.sujet_year.value = item.year || "";
  form.elements.sujet_motto.value = item.motto || "";
  form.elements.sujet_logo_file.value = "";
  document.getElementById("sujet-logo-current").textContent = item.logo_url ? "Logo gespeichert" : "";
  form.elements.sujet_is_current.checked = item.is_current === true;
''',
    "pc sujet edit motto logo",
)
text = replace_once(
    text,
    '''        title: contentPayload.title,
        text: contentPayload.text,
        is_current: form.elements.sujet_is_current.checked,
''',
    '''        title: contentPayload.title,
        motto: form.elements.sujet_motto.value.trim(),
        text: contentPayload.text,
        is_current: form.elements.sujet_is_current.checked,
''',
    "pc sujet payload motto",
)
# upload logo after annual saved and before image files
needle = '''  const documentFile = form.elements.document_file.files[0];
'''
insert = '''  if (isAnnualSujet) {
    const logoFile = form.elements.sujet_logo_file.files[0];
    if (logoFile) {
      const logoUpload = new FormData();
      logoUpload.append("logo", logoFile);
      await api(`/api/sujets/${saved.id}/logo`, {method:"POST", body:logoUpload});
    }
  }

''' + needle
text = replace_once(text, needle, insert, "pc sujet logo upload")
path.write_text(text, encoding="utf-8")


# ---------------- Version ----------------
path = Path("pubspec.yaml")
text = path.read_text(encoding="utf-8")
text = re.sub(r"^version:\s*[^\n]+", "version: 0.9.1+37", text, count=1, flags=re.MULTILINE)
path.write_text(text, encoding="utf-8")

print("Phase 3-5 completion migration applied")
