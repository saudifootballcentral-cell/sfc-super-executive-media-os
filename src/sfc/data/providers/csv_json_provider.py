"""CSV/JSON manual import provider for Package 10A."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sfc.data.providers.base import BaseDataProvider

logger = logging.getLogger("sfc.data.providers.csv_json")

_IMPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "imports"


class CSVJSONProvider(BaseDataProvider):
    """Reads manually uploaded CSV or JSON files from data/imports/ directory."""

    def __init__(self, imports_dir: Path | None = None) -> None:
        self._imports_dir = imports_dir or _IMPORTS_DIR

    @property
    def data_source(self) -> str:
        return "csv_import"

    def is_available(self) -> bool:
        return self._imports_dir.exists() and any(self._imports_dir.iterdir()) if self._imports_dir.exists() else False

    async def fetch(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        file_path = kwargs.get("file_path")
        if file_path:
            return self._read_file(Path(file_path), query)

        results: list[dict[str, Any]] = []
        if not self._imports_dir.exists():
            return results

        for path in self._imports_dir.iterdir():
            if path.suffix in (".json", ".csv"):
                results.extend(self._read_file(path, query))

        logger.info("[CSVJSONProvider] Found %d records from imports dir", len(results))
        return results

    def _read_file(self, path: Path, query: str) -> list[dict[str, Any]]:
        try:
            if path.suffix == ".json":
                return self._read_json(path, query)
            if path.suffix == ".csv":
                return self._read_csv(path, query)
            return []
        except Exception as exc:
            logger.warning("[CSVJSONProvider] Failed to read %s: %s", path, exc)
            return []

    def _read_json(self, path: Path, query: str) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        records = data if isinstance(data, list) else data.get("items", data.get("data", [data]))
        for r in records:
            r.setdefault("collected_at", datetime.utcnow().isoformat())
            r.setdefault("source_url", str(path))
        return records

    def _read_csv(self, path: Path, query: str) -> list[dict[str, Any]]:
        results = []
        with path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row.setdefault("collected_at", datetime.utcnow().isoformat())
                row.setdefault("source_url", str(path))
                results.append(dict(row))
        return results
