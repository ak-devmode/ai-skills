"""Export notes as plain text."""
import os

from notes.exporters.registry import ExporterRegistry
from notes.store import all_notes

BUCKET = os.environ.get("{{ENV}}")


def export_text():
    return ExporterRegistry.default().get("text").export(all_notes())
