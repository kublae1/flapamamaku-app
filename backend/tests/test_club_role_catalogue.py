from __future__ import annotations

from fastapi import HTTPException

from app.main import (
    BootstrapPayload,
    UserPayload,
    bootstrap,
    get_roles,
    init_db,
    post_user,
)


def main() -> None:
    init_db()
    root = bootstrap(
        BootstrapPayload(
            username='role-root',
            password='Testpass123!',
            member_id=None,
        )
    )
    roles = get_roles(_=root)
    keys = [row['key'] for row in roles]
    assert keys == ['member', 'editor', 'board', 'club_manager']
    manager = next(row for row in roles if row['key'] == 'club_manager')
    assert manager['label'] == 'Vereinsverwaltung'
    assert all(manager['permissions'].values())
    assert 'admin' not in keys

    created = post_user(
        UserPayload(
            username='club-manager',
            password='Testpass123!',
            role_key='club_manager',
        ),
        _=root,
    )
    assert created['role_key'] == 'club_manager'
    assert created['club_role'] == 'club_admin'
    for permission, enabled in manager['permissions'].items():
        assert created[permission] is enabled, permission

    try:
        post_user(
            UserPayload(
                username='forbidden-platform-admin',
                password='Testpass123!',
                role_key='admin',
            ),
            _=root,
        )
        raise AssertionError('internal Administrator role was assignable through API')
    except HTTPException as exc:
        assert exc.status_code == 422

    print('club role catalogue ok')


if __name__ == '__main__':
    main()
