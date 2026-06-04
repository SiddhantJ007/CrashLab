import json
from pathlib import Path
from typing import Dict, List

from app.core.store import list_configured_targets


# Bootstrap targets from targets.json are merged with UI-created targets from SQLite.
# Later entries win so a user can replace or refine an example target without editing files.
def load_targets(path: Path) -> Dict[str, List[Dict]]:
    bootstrap = {"targets": []}
    if path.exists():
        with open(path, "r", encoding="utf-8") as handle:
            bootstrap = json.load(handle)

    merged = {}
    for target in bootstrap.get("targets", []):
        merged[target["id"]] = {**target, "target_source": target.get("target_source", "bootstrap_targets_json")}
    for target in list_configured_targets():
        merged[target["id"]] = {**target, "target_source": target.get("target_source", "onboarded_sqlite")}
    return {"targets": list(merged.values())}
