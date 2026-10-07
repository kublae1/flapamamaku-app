from pathlib import Path

path = Path('backend/app/main.py')
text = path.read_text(encoding='utf-8')

block = '''        db.execute(
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

'''
if text.count(block) != 1:
    raise SystemExit(f'expected one early backfill block, found {text.count(block)}')
text = text.replace(block, '', 1)

marker = '''        for table in (*direct_club_tables, *relation_club_tables):
            _ensure_club_column(db, table)

'''
if text.count(marker) != 1:
    raise SystemExit(f'expected one club-column loop, found {text.count(marker)}')
text = text.replace(marker, marker + block, 1)

path.write_text(text, encoding='utf-8')
print('scoped member backfill moved after club-column migration')
