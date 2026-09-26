"""Pluggable exporter registry — register exporters by name, resolve them at runtime."""
import importlib


class Exporter:
    name = None

    def export(self, notes):
        raise NotImplementedError


class TextExporter(Exporter):
    name = "text"

    def export(self, notes):
        return "\n".join(notes)


class ExporterRegistry:
    _default = None

    def __init__(self):
        self._exporters = {}

    def register(self, exporter_cls):
        self._exporters[exporter_cls.name] = exporter_cls
        return exporter_cls

    def load_plugin(self, dotted):
        module, _, cls = dotted.rpartition(".")
        return self.register(getattr(importlib.import_module(module), cls))

    def get(self, name):
        return self._exporters[name]()

    @classmethod
    def default(cls):
        if cls._default is None:
            cls._default = cls()
            cls._default.register(TextExporter)
        return cls._default
