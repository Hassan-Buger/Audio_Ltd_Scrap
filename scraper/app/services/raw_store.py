"""Durable raw HTML snapshot store for offline caching, replaying, and auditability."""
from __future__ import annotations
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"


class RawStore:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or SNAPSHOT_DIR
        self.root.mkdir(parents=True, exist_ok=True)

    def _hash(self, url: str) -> str:
        clean = url.strip().rstrip("/")
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:32]

    def has(self, url: str) -> bool:
        base = self.root / self._hash(url)
        return base.with_suffix(".html").exists()

    def save(
        self,
        url: str,
        html_text: str,
        status_code: int = 200,
        final_url: Optional[str] = None
    ) -> Path:
        """Save a raw HTML snapshot and metadata JSON to disk."""
        base = self.root / self._hash(url)
        html_path = base.with_suffix(".html")
        meta_path = base.with_suffix(".json")

        html_path.write_text(html_text, encoding="utf-8")
        meta = {
            "url": url,
            "final_url": final_url or url,
            "status": status_code,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "content_length": len(html_text),
            "sha256": hashlib.sha256(html_text.encode("utf-8")).hexdigest()
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Saved raw HTML snapshot for {url} ({len(html_text)} bytes)")
        return html_path

    def load(self, url: str) -> Optional[Dict[str, Any]]:
        """Load an existing HTML snapshot for a given URL if cached on disk."""
        base = self.root / self._hash(url)
        html_path = base.with_suffix(".html")
        meta_path = base.with_suffix(".json")

        if not html_path.exists():
            return None

        text = html_path.read_text(encoding="utf-8")
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "url": url,
            "final_url": meta.get("final_url", url),
            "status": meta.get("status", 200),
            "text": text,
            "saved_at": meta.get("saved_at")
        }

    def ingest_file(self, url: str, file_path: Path | str, final_url: Optional[str] = None) -> bool:
        """Ingest a pre-saved HTML file from disk into the raw snapshot store."""
        path = Path(file_path)
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8", errors="replace")
        self.save(url=url, html_text=content, status_code=200, final_url=final_url)
        return True

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots."""
        results = []
        for meta_file in self.root.glob("*.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                html_file = meta_file.with_suffix(".html")
                if html_file.exists():
                    data["file_path"] = str(html_file)
                    results.append(data)
            except Exception:
                continue
        return results


raw_store = RawStore()
