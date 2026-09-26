"""An in-memory, append-only note store."""
import os

DB_URL = os.environ.get("NOTES_DB_URL", "sqlite:///notes.db")
_NOTES = []


def add(text):
    _NOTES.append(text)
    return len(_NOTES)


def all_notes():
    return list(_NOTES)
