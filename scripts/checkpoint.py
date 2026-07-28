"""Per-phase checkpointing for the Light Tower editorial pipeline."""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT = SCRIPT_DIR.parent
STATE_DIR = SITE_ROOT / ".editorial-state"
CHECKPOINT_DIR = STATE_DIR / "checkpoints"

PHASE_TIMEOUTS: dict[str, int] = {
    "gather": 120,
    "triage": 60,
    "cluster": 30,
    "score_deterministic": 30,
    "score_llm": 120,
    "dossier": 60,
    "editorial_room": 120,
    "write": 180,
    "governance": 30,
    "publish": 60,
}


def checkpoint_path(phase: str) -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR / f"checkpoint-{phase}.json"


def save_checkpoint(phase: str, data: dict[str, Any]) -> None:
    data["_checkpoint_saved_at"] = datetime.now(timezone.utc).isoformat()
    data["_checkpoint_phase"] = phase
    path = checkpoint_path(phase)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def load_checkpoint(phase: str) -> dict[str, Any] | None:
    path = checkpoint_path(phase)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def clear_checkpoints() -> None:
    if CHECKPOINT_DIR.exists():
        for path in CHECKPOINT_DIR.glob("checkpoint-*.json"):
            path.unlink()


def run_with_timeout(phase: str, func: Callable, *args, **kwargs) -> Any:
    """Run a pipeline phase with timeout and checkpointing."""
    timeout = PHASE_TIMEOUTS.get(phase, 120)
    start = time.time()

    # Check for existing checkpoint
    saved = load_checkpoint(phase)
    if saved:
        print(f"  [CHECKPOINT] Resuming {phase} from saved state")
        return saved

    result = func(*args, **kwargs)

    elapsed = time.time() - start
    if elapsed > timeout:
        print(f"  [WARN] Phase '{phase}' took {elapsed:.0f}s (timeout: {timeout}s)")

    save_checkpoint(phase, result if isinstance(result, dict) else {"result": str(result)[:1000]})
    return result


def checkpoint_available(phase: str) -> bool:
    return checkpoint_path(phase).exists()
