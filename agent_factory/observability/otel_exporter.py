from __future__ import annotations


class OTelExporter:
    def export(self, event_name: str, payload: dict) -> None:
        _ = (event_name, payload)
