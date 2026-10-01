from __future__ import annotations

from fastapi import HTTPException

from app import main as main_module
from app.main import (
    BootstrapPayload,
    SuperAdminRecoveryPayload,
    SuperAdminRolePayload,
    UserPayload,
    bootstrap,
    connect,
    delete_user,
    init_db,
    post_user,
    recover_super_admin,
    set_super_admin_role,
)


def must_fail_400(fn) -> None:
    try:
        fn()
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("expected HTTP 400")


def main() -> None:
    init_db()
    root = bootstrap(BootstrapPayload(username="root-admin", password="Testpass123!", member_id=None))
    assert root["is_super_admin"] is True

    second = post_user(
        UserPayload(username="second-admin", password="Testpass123!", active=True, role_key="club_manager"),
        root,
    )
    promoted = set_super_admin_role(
        second["id"],
        SuperAdminRolePayload(enabled=True),
        actor=root,
    )
    assert promoted["is_super_admin"] is True

    demoted_root = set_super_admin_role(
        root["id"],
        SuperAdminRolePayload(enabled=False),
        actor=root,
    )
    assert demoted_root["is_super_admin"] is False

    must_fail_400(
        lambda: set_super_admin_role(
            second["id"],
            SuperAdminRolePayload(enabled=False),
            actor=promoted,
        )
    )
    must_fail_400(lambda: delete_user(second["id"], actor=root))

    main_module.SUPERADMIN_RECOVERY_TOKEN = "test-recovery-code-123456"
    recovered = recover_super_admin(
        SuperAdminRecoveryPayload(
            recovery_token="test-recovery-code-123456",
            username="emergency-admin",
            password="Emergency123!",
        )
    )
    assert recovered["recovered"] is True

    with connect() as db:
        row = db.execute(
            "SELECT id FROM users WHERE username = ?",
            ("emergency-admin",),
        ).fetchone()
        assert row is not None
        role = db.execute(
            "SELECT role FROM user_clubs WHERE user_id = ? AND club_id = 1",
            (row["id"],),
        ).fetchone()
        assert role is not None and role["role"] == "super_admin"
        event_types = {
            item["event_type"]
            for item in db.execute("SELECT event_type FROM security_events").fetchall()
        }
        assert {"super_admin_granted", "super_admin_revoked", "super_admin_recovery"}.issubset(event_types)

    final = set_super_admin_role(
        second["id"],
        SuperAdminRolePayload(enabled=False),
        actor={"id": recovered["user_id"], "is_super_admin": True},
    )
    assert final["is_super_admin"] is False
    print("super-admin resilience ok")


if __name__ == "__main__":
    main()
