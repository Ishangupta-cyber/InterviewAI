"""Shared contract that every model module in this project must follow.

The whole architecture is hub-and-spoke: the 5 scoring models never talk to
each other, they only return a ModuleResult, and fusion.py is the only place
where the modalities are ever combined.

To implement a real module, edit ONLY that module's file and:
  1. flip MODULE_INFO["status"] from "stub" to "live"
  2. replace the body of analyze() with real inference
Nothing else in the codebase needs to change.
"""

import hashlib
import random
from dataclasses import dataclass, field, asdict


@dataclass
class ModuleResult:
    module_id: str
    name: str
    score: float                      # 0-100, higher is better
    status: str = "stub"              # "stub" while mocked, "live" once real
    metrics: dict = field(default_factory=dict)   # raw numbers this model measured
    notes: list = field(default_factory=list)     # human-readable feedback lines

    def to_dict(self):
        d = asdict(self)
        d["score"] = round(self.score, 1)
        return d


def seeded_random(session_id: str, module_id: str) -> random.Random:
    """Deterministic per (session, module) so a demo replays identically
    but different sessions look different. Only used by stubs."""
    seed = int(hashlib.md5(f"{session_id}:{module_id}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)
