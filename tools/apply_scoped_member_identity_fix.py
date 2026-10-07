from pathlib import Path

path = Path('backend/app/main.py')
text = path.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count}')
    text = text.replace(old, new, 1)


# 1. Add the per-club member identity relation and hard DB guards.
marker = '''        db.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
'''
insert = '''        db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_club_members (
                user_id INTEGER NOT NULL,
                club_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, club_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(club_id) REFERENCES clubs(id),
                FOREIGN KEY(member_id) REFERENCES members(id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_club_members_member_id "
            "ON user_club_members(member_id)"
        )
        db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_user_club_members_insert_scope
            BEFORE INSERT ON user_club_members
            WHEN NOT EXISTS (
                SELECT 1 FROM members m
                WHERE m.id = NEW.member_id AND m.club_id = NEW.club_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'member_id belongs to another club');
            END
            """
        )
        db.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_user_club_members_update_scope
            BEFORE UPDATE OF club_id, member_id ON user_club_members
            WHEN NOT EXISTS (
                SELECT 1 FROM members m
                WHERE m.id = NEW.member_id AND m.club_id = NEW.club_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'member_id belongs to another club');
            END
            """
        )

''' + marker
replace_once(marker, insert, 'identity table insertion')

# 2. Backfill only mappings where the legacy global member actually belongs to
#    one of that user's existing club memberships.
marker = '''        # Repair memberships created by the previous legacy migration.
'''
insert = '''        db.execute(
            """
            INSERT OR IGNORE INTO user_club_members (user_id, club_id, member_id)
            SELECT u.id, m.club_id, m.id
            FROM users u
            JOIN members m ON m.id = u.member_id
            JOIN user_clubs uc
              ON uc.user_id = u.id
             AND uc.club_id = m.club_id
            WHERE u.member_id IS NOT NULL
            """
        )

''' + marker
replace_once(marker, insert, 'identity backfill')

# 3. Scope individual user profiles to the active club.
old = '''            SELECT
                u.*,
                m.name AS member_name
            FROM users u
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = ?
            WHERE u.id = ?
            """,
            (club_id, user_id),
'''
new = '''            SELECT
                u.*,
                ucm.member_id AS scoped_member_id,
                m.name AS member_name
            FROM users u
            LEFT JOIN user_club_members ucm
              ON ucm.user_id = u.id
             AND ucm.club_id = ?
            LEFT JOIN members m
              ON m.id = ucm.member_id
             AND m.club_id = ?
            WHERE u.id = ?
            """,
            (club_id, club_id, user_id),
'''
replace_once(old, new, 'user profile query')
old = '''        item = dict(row)
        item["club_role"] = club_role
'''
new = '''        item = dict(row)
        item["member_id"] = item.pop("scoped_member_id", None)
        item["club_role"] = club_role
'''
replace_once(old, new, 'user profile scoped member output')

# 4. Scope the authenticated identity to the session's active club.
old = '''            SELECT u.*, s.active_club_id, m.name AS member_name
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = s.active_club_id
'''
new = '''            SELECT
                u.*,
                s.active_club_id,
                ucm.member_id AS scoped_member_id,
                m.name AS member_name
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN user_club_members ucm
              ON ucm.user_id = u.id
             AND ucm.club_id = s.active_club_id
            LEFT JOIN members m
              ON m.id = ucm.member_id
             AND m.club_id = s.active_club_id
'''
replace_once(old, new, 'current user query')
old = '''        item = dict(row)
        item["club_role"] = club_role
        item["current_club_id"] = club_id
        item["is_super_admin"] = _is_super_admin(db, int(row["id"]))
    return _serialize_user(item)


def require(permission: str):
'''
new = '''        item = dict(row)
        item["member_id"] = item.pop("scoped_member_id", None)
        item["club_role"] = club_role
        item["current_club_id"] = club_id
        item["is_super_admin"] = _is_super_admin(db, int(row["id"]))
    return _serialize_user(item)


def require(permission: str):
'''
replace_once(old, new, 'current user scoped member output')

# 5. Scope the club user list.
old = '''            SELECT
                u.*,
                m.name AS member_name,
                uc.role AS club_role,
                uc.club_id AS current_club_id
            FROM users u
            JOIN user_clubs uc
              ON uc.user_id = u.id
             AND uc.club_id = ?
             AND uc.active = 1
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = uc.club_id
'''
new = '''            SELECT
                u.*,
                ucm.member_id AS scoped_member_id,
                m.name AS member_name,
                uc.role AS club_role,
                uc.club_id AS current_club_id
            FROM users u
            JOIN user_clubs uc
              ON uc.user_id = u.id
             AND uc.club_id = ?
             AND uc.active = 1
            LEFT JOIN user_club_members ucm
              ON ucm.user_id = u.id
             AND ucm.club_id = uc.club_id
            LEFT JOIN members m
              ON m.id = ucm.member_id
             AND m.club_id = uc.club_id
'''
replace_once(old, new, 'club users query')
old = '''        for row in rows:
            item = dict(row)
            item["is_super_admin"] = _is_super_admin(db, int(row["id"]))
            result.append(_serialize_user(item))
'''
new = '''        for row in rows:
            item = dict(row)
            item["member_id"] = item.pop("scoped_member_id", None)
            item["is_super_admin"] = _is_super_admin(db, int(row["id"]))
            result.append(_serialize_user(item))
'''
replace_once(old, new, 'club users scoped output')

# 6. Validate and store the scoped mapping when a user is created.
old = '''    with connect() as db:
        try:
            cursor = db.execute(
'''
new = '''    with connect() as db:
        club_id = _active_club_id(db)
        if payload.member_id is not None:
            member = db.execute(
                "SELECT id FROM members WHERE id = ? AND club_id = ?",
                (payload.member_id, club_id),
            ).fetchone()
            if member is None:
                raise HTTPException(
                    status_code=422,
                    detail="Mitglied gehört nicht zum aktiven Verein",
                )
        try:
            cursor = db.execute(
'''
# This exact pattern also occurs elsewhere; anchor it to the post_user body.
post_anchor = 'def post_user(\n'
pos = text.index(post_anchor)
tail = text[pos:]
if tail.count(old) < 1:
    raise SystemExit('post user connection block not found')
tail = tail.replace(old, new, 1)
text = text[:pos] + tail

old = '''                    user_id,
                    _active_club_id(db),
                    club_role,
'''
new = '''                    user_id,
                    club_id,
                    club_role,
'''
replace_once(old, new, 'post user club id')
old = '''            )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Benutzername bereits vorhanden")
    return _user_profile(user_id)


@app.put("/api/users/{user_id}")
'''
new = '''            )
            if payload.member_id is not None:
                db.execute(
                    """
                    INSERT INTO user_club_members (user_id, club_id, member_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, club_id)
                    DO UPDATE SET member_id = excluded.member_id
                    """,
                    (user_id, club_id, payload.member_id),
                )
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Benutzername bereits vorhanden")
    return _user_profile(user_id)


@app.put("/api/users/{user_id}")
'''
replace_once(old, new, 'post user scoped mapping')

# 7. Validate/update only the active club's member mapping on user edits.
old = '''        if target is None:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        target_role = db.execute(
'''
new = '''        if target is None:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        if payload.member_id is not None:
            member = db.execute(
                "SELECT id FROM members WHERE id = ? AND club_id = ?",
                (payload.member_id, club_id),
            ).fetchone()
            if member is None:
                raise HTTPException(
                    status_code=422,
                    detail="Mitglied gehört nicht zum aktiven Verein",
                )
        target_role = db.execute(
'''
replace_once(old, new, 'put user member validation')
old = '''            if password_changed:
                db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.commit()
'''
new = '''            if payload.member_id is None:
                db.execute(
                    "DELETE FROM user_club_members WHERE user_id = ? AND club_id = ?",
                    (user_id, club_id),
                )
            else:
                db.execute(
                    """
                    INSERT INTO user_club_members (user_id, club_id, member_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, club_id)
                    DO UPDATE SET member_id = excluded.member_id
                    """,
                    (user_id, club_id, payload.member_id),
                )
            if password_changed:
                db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.commit()
'''
replace_once(old, new, 'put user scoped mapping')

path.write_text(text, encoding='utf-8')
print('scoped member identity patch applied')
