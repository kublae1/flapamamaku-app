"""Static Phase-2 contract for the PC admin CMS.

The goal is not pixel testing. It prevents accidental removal of the binding
CMS structure agreed for Phase 2: central navigation, CRUD workspaces, upload
controls, settings separation, previews and delete confirmations.
"""

from __future__ import annotations

from pathlib import Path
import sys

ADMIN = Path(__file__).resolve().parents[1] / "static" / "admin.html"


def fail(message: str) -> None:
    print(f"PHASE2 CMS CONTRACT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(text: str, needle: str, label: str | None = None) -> None:
    if needle not in text:
        fail(f"missing {label or needle}")


def main() -> None:
    text = ADMIN.read_text(encoding="utf-8")

    # Binding main CMS navigation.
    for panel, label in (
        ("news", "News"),
        ("events", "Termine"),
        ("members", "Mitglieder"),
        ("users", "Benutzer & Rechte"),
        ("content", "Medien & Inhalte"),
        ("system", "Verein & System"),
    ):
        require(text, f'data-panel="{panel}"', f"navigation panel {label}")

    # Core editor forms.
    for form_id in (
        "news-form",
        "events-form",
        "members-form",
        "users-form",
        "content-form",
        "app-config-form",
    ):
        require(text, f'id="{form_id}"', f"form {form_id}")

    # CMS needs real media uploads, not hardcoded local asset selectors.
    require(text, 'name="image_file" type="file"', "news image upload")
    require(text, 'name="photo_file" type="file"', "member photo upload")
    require(text, 'type="file"', "file upload controls")

    # Phase-2 visual feedback and previews.
    require(text, "phone-preview", "phone/app preview")
    require(text, "existing-images", "existing image preview/management")
    require(text, 'id="status"', "central status area")

    # Destructive actions must ask for confirmation.
    confirmations = text.count("confirm(")
    if confirmations < 5:
        fail(f"expected several delete confirmations, found only {confirmations}")

    # Keep settings separate from ordinary content editing.
    require(text, 'data-panel="system"', "separate system/settings panel")
    require(text, 'id="app-config-form"', "club configuration form")

    # No legacy local club-image chooser is allowed in the browser CMS.
    for forbidden in (
        "assets/images/year_motto_pig_rockers.jpg",
        "assets/images/archive_top_hats_night.jpg",
        "assets/images/archive_vikings_bar.jpg",
    ):
        if forbidden in text:
            fail(f"hardcoded club asset leaked into CMS: {forbidden}")

    print("PHASE2 CMS CONTRACT OK")


if __name__ == "__main__":
    main()
