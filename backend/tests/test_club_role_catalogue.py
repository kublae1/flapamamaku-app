from __future__ import annotations

from app.main import BootstrapPayload, get_roles, init_db, bootstrap


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
    print('club role catalogue ok')


if __name__ == '__main__':
    main()
