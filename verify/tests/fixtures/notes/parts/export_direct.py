"""Export notes as plain text."""
import os

from notes.store import all_notes

BUCKET = os.environ.get("{{ENV}}")


def export_text():
    return "\n".join(all_notes())
