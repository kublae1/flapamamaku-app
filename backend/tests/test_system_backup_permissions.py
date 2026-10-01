from __future__ import annotations

import asyncio
import io

from fastapi import HTTPException, UploadFile

from app.main import (
    BootstrapPayload,
    UserPayload,
    bootstrap,
    create_backup,
    download_backup,
    init_db,
    post_user,
    restore_backup,
)


def _expect_403(action) -> None:
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError('Expected HTTP 403')


async def _restore_denied(club_admin: dict) -> None:
    upload = UploadFile(
        filename='backup.db',
        file=io.BytesIO(b'not-used'),
    )
    try:
        await restore_backup(backup_file=upload, user=club_admin)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError('Expected restore HTTP 403')


def main() -> None:
    init_db()
    super_user = bootstrap(
        BootstrapPayload(
            username='root-admin',
            password='Testpass123!',
            member_id=None,
        )
    )
    club_admin = post_user(
        UserPayload(
            member_id=None,
            username='club-admin',
            password='Testpass123!',
            active=True,
            role_key='admin',
            permission_overrides={},
        ),
        _=super_user,
    )

    _expect_403(lambda: create_backup(user=club_admin))
    _expect_403(lambda: download_backup('anything.db', user=club_admin))
    asyncio.run(_restore_denied(club_admin))

    created = create_backup(user=super_user)
    assert created['name'].endswith('.db')

    admin_html = open('static/admin.html', encoding='utf-8').read()
    assert 'system-admin-backup-card' in admin_html
    assert 'Nur für Super-Admins.' in admin_html
    assert 'activeClubConfig = null;' in admin_html
    assert 'accessibleClubs = [];' in admin_html
    assert 'API online · v' in admin_html

    print('system backup permissions and logout status ok')


if __name__ == '__main__':
    main()
