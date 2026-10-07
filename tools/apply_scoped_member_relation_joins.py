from pathlib import Path

path = Path('backend/app/main.py')
text = path.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one match, found {count}')
    text = text.replace(old, new, 1)

# Poll vote names: resolve through the poll's owning club.
replace_once(
'''                FROM poll_votes pv
                JOIN users u ON u.id = pv.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE pv.poll_id = ?
''',
'''                FROM poll_votes pv
                JOIN users u ON u.id = pv.user_id
                JOIN content_items poll ON poll.id = pv.poll_id
                LEFT JOIN user_club_members ucm
                  ON ucm.user_id = u.id
                 AND ucm.club_id = poll.club_id
                LEFT JOIN members m
                  ON m.id = ucm.member_id
                 AND m.club_id = poll.club_id
                WHERE pv.poll_id = ?
''',
'poll vote identity',
)

# Poll suggestion names: same rule.
replace_once(
'''                FROM poll_suggestions ps
                JOIN users u ON u.id = ps.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE ps.poll_id = ?
''',
'''                FROM poll_suggestions ps
                JOIN users u ON u.id = ps.user_id
                JOIN content_items poll ON poll.id = ps.poll_id
                LEFT JOIN user_club_members ucm
                  ON ucm.user_id = u.id
                 AND ucm.club_id = poll.club_id
                LEFT JOIN members m
                  ON m.id = ucm.member_id
                 AND m.club_id = poll.club_id
                WHERE ps.poll_id = ?
''',
'poll suggestion identity',
)

# Snapshot returned after upload.
replace_once(
'''            FROM gallery_snapshots gs
            JOIN users u ON u.id = gs.user_id
            LEFT JOIN members m
              ON m.id = u.member_id
             AND m.club_id = gs.club_id
            WHERE gs.id = ? AND gs.club_id = ?
''',
'''            FROM gallery_snapshots gs
            JOIN users u ON u.id = gs.user_id
            LEFT JOIN user_club_members ucm
              ON ucm.user_id = u.id
             AND ucm.club_id = gs.club_id
            LEFT JOIN members m
              ON m.id = ucm.member_id
             AND m.club_id = gs.club_id
            WHERE gs.id = ? AND gs.club_id = ?
''',
'gallery snapshot upload identity',
)

# Snapshot listing.
replace_once(
'''                FROM gallery_snapshots gs
                JOIN users u ON u.id = gs.user_id
                LEFT JOIN members m ON m.id = u.member_id
                WHERE gs.expires_at > ? AND gs.club_id = ?
''',
'''                FROM gallery_snapshots gs
                JOIN users u ON u.id = gs.user_id
                LEFT JOIN user_club_members ucm
                  ON ucm.user_id = u.id
                 AND ucm.club_id = gs.club_id
                LEFT JOIN members m
                  ON m.id = ucm.member_id
                 AND m.club_id = gs.club_id
                WHERE gs.expires_at > ? AND gs.club_id = ?
''',
'gallery snapshot list identity',
)

# Event participant names.
replace_once(
'''            FROM event_registrations r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN members m ON m.id = u.member_id
            WHERE r.event_id = ?
              AND r.club_id = ?
''',
'''            FROM event_registrations r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN user_club_members ucm
              ON ucm.user_id = u.id
             AND ucm.club_id = r.club_id
            LEFT JOIN members m
              ON m.id = ucm.member_id
             AND m.club_id = r.club_id
            WHERE r.event_id = ?
              AND r.club_id = ?
''',
'event registration identity',
)

path.write_text(text, encoding='utf-8')
print('scoped member relation joins applied')
