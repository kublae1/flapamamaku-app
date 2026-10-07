import os
import sqlite3
import tempfile
from contextlib import contextmanager

from app import message_center


fd, path = tempfile.mkstemp(prefix="flapamamaku-messages-", suffix=".db")
os.close(fd)

try:
    db = sqlite3.connect(path)
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
    assert rows[0]["urgent"] is True
    assert rows[1]["urgent"] is False
    assert all(row["read"] is False for row in rows)
    assert message_center.unread_message_count(user=user_1)["unread"] == 2

    message_center.mark_message_read(rows[0]["id"], user=user_1)
    refreshed = message_center.list_messages(user=user_1)
    assert refreshed[0]["read"] is True
    assert refreshed[1]["read"] is False
    assert message_center.unread_message_count(user=user_1)["unread"] == 1

    # Read state is personal, not global within the club.
    other_user_rows = message_center.list_messages(user=user_2)
    assert all(row["read"] is False for row in other_user_rows)

    # Tenant isolation: club 2 sees only club 2's notification.
    club_2_rows = message_center.list_messages(user=club_2_user)
    assert [row["title"] for row in club_2_rows] == ["Verein 2"], club_2_rows

    message_center.mark_all_messages_read(user=user_1)
    assert message_center.unread_message_count(user=user_1)["unread"] == 0
    assert message_center.unread_message_count(user=user_2)["unread"] == 2

    print("message center tenant/read-state contract: OK")
finally:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
