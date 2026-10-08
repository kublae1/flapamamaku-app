import os
import sqlite3
import tempfile
from contextlib import contextmanager

from app import message_center


fd, path = tempfile.mkstemp(prefix="flapamamaku-messages-", suffix=".db")
os.close(fd)

try:
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
    db.execute("CREATE TABLE clubs (id INTEGER PRIMARY KEY)")
    db.executemany("INSERT INTO users(id) VALUES (?)", [(10,), (11,), (12,)])
    db.executemany("INSERT INTO clubs(id) VALUES (?)", [(1,), (2,)])
    db.execute(
        """
        CREATE TABLE push_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            route TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            club_id INTEGER NOT NULL
        )
        """
    )
    db.execute(
        "INSERT INTO push_notifications(kind,title,body,route,created_at,club_id) VALUES (?,?,?,?,?,?)",
        ("manual", "Verein 1", "Normal", "/messages", "2026-10-07T20:00:00+00:00", 1),
    )
    db.execute(
        "INSERT INTO push_notifications(kind,title,body,route,created_at,club_id) VALUES (?,?,?,?,?,?)",
        ("manual_urgent", "Dringend", "Wichtig", "/messages", "2026-10-07T20:01:00+00:00", 1),
    )
    db.execute(
        "INSERT INTO push_notifications(kind,title,body,route,created_at,club_id) VALUES (?,?,?,?,?,?)",
        ("manual", "Verein 2", "Fremd", "/messages", "2026-10-07T20:02:00+00:00", 2),
    )
    db.commit()
    db.close()

    @contextmanager
    def test_connect():
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    message_center.main_app.connect = test_connect
    message_center.init_message_center_schema()

    user_1 = {"id": 10, "current_club_id": 1}
    user_2 = {"id": 11, "current_club_id": 1}
    club_2_user = {"id": 12, "current_club_id": 2}

    rows = message_center.list_messages(user=user_1)
    assert [row["title"] for row in rows] == ["Dringend", "Verein 1"], rows
    assert all(row["read"] is False for row in rows)
    assert message_center.unread_message_count(user=user_1)["unread"] == 2

    message_center.mark_message_read(rows[0]["id"], user=user_1)
    assert message_center.unread_message_count(user=user_1)["unread"] == 1

    # Delete is personal: user 1 hides one message, user 2 still sees both.
    message_center.delete_message_for_user(rows[0]["id"], user=user_1)
    assert [row["title"] for row in message_center.list_messages(user=user_1)] == ["Verein 1"]
    assert len(message_center.list_messages(user=user_2)) == 2

    # Tenant isolation remains intact.
    assert [row["title"] for row in message_center.list_messages(user=club_2_user)] == ["Verein 2"]

    message_center.mark_all_messages_read(user=user_1)
    assert message_center.unread_message_count(user=user_1)["unread"] == 0
    message_center.delete_read_messages_for_user(user=user_1)
    assert message_center.list_messages(user=user_1) == []
    assert len(message_center.list_messages(user=user_2)) == 2

    # Delete all is also personal and scoped to current club.
    message_center.delete_all_messages_for_user(user=user_2)
    assert message_center.list_messages(user=user_2) == []
    assert [row["title"] for row in message_center.list_messages(user=club_2_user)] == ["Verein 2"]

    print("message center tenant/read/delete contract: OK")
finally:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
