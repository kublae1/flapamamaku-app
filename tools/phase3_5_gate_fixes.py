from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing source anchor: {label}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "lib/screens/content_detail_screens.dart",
    """  Future<void> _addToCalendar() async {\n    final result = await _ask(\n      'Kalender',\n      '„${widget.event.title}“ in den Kalender eintragen?',\n    );\n    if (result != null && mounted) setState(() => inCalendar = result);\n  }\n\n  @override\n""",
    """  Future<void> _addToCalendar() async {\n    final result = await _ask(\n      'Kalender',\n      '„${widget.event.title}“ in den Kalender eintragen?',\n    );\n    if (result != null && mounted) setState(() => inCalendar = result);\n  }\n\n  Future<void> _launch(BuildContext context, Uri uri) async {\n    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);\n    if (!ok && context.mounted) {\n      ScaffoldMessenger.of(context).showSnackBar(\n        const SnackBar(content: Text('Aktion konnte nicht geöffnet werden.')),\n      );\n    }\n  }\n\n  @override\n""",
    "event external launcher",
)

replace_once(
    "backend/app/phase45.py",
    '@app.delete("/api/sujets/{sujet_id}/logo", status_code=204)',
    '@app.delete("/api/sujets/{sujet_id}/logo")',
    "sujet logo delete route",
)

print("Phase 3-5 gate fixes applied")
