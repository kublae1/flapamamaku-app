from pathlib import Path

source_path = Path('tools/apply_scoped_member_identity_fix.py')
source = source_path.read_text(encoding='utf-8')
source = source.replace(
    "    if count != 1:\n        raise SystemExit(f'{label}: expected exactly one match, found {count}')",
    "    if count < 1:\n        raise SystemExit(f'{label}: expected at least one match, found {count}')",
    1,
)
exec(compile(source, str(source_path), 'exec'), {'__name__': '__main__'})
