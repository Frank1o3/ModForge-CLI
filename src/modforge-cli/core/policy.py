from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, TypedDict
from urllib.parse import urlparse
from urllib.request import urlopen
from collections import deque

from jsonschema import ValidationError, validate


class NormalizedModRule(TypedDict):
    conflicts: Set[str]
    sub_mods: Set[str]


NormalizedPolicyRules = Dict[str, NormalizedModRule]


class PolicyError(RuntimeError):
    pass


# -------- schema cache (performance + offline safety) --------
_SCHEMA_CACHE: Dict[str, dict] = {}


def _load_schema(schema_ref: str, base_path: Path) -> dict:
    if schema_ref in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[schema_ref]

    parsed = urlparse(schema_ref)

    try:
        if parsed.scheme in ("http", "https", "file"):
            with urlopen(schema_ref) as resp:
                schema = json.load(resp)
        else:
            schema_path = (base_path.parent / schema_ref).resolve()
            if not schema_path.exists():
                raise PolicyError(f"Schema not found: {schema_path}")
            schema = json.loads(schema_path.read_text())
    except Exception as e:
        raise PolicyError(f"Failed to load schema '{schema_ref}': {e}") from e

    _SCHEMA_CACHE[schema_ref] = schema
    return schema


class ModPolicy:
    """
    Enforces mod compatibility rules:
    - removes conflicts
    - injects recommended sub-mods
    """

    def __init__(self, policy_path: str | Path = "configs/policy.json"):
        self.policy_path = policy_path if isinstance(policy_path, Path) else Path(policy_path)
        self.rules: NormalizedPolicyRules = {}
        self.schema_ref: str | None = None

        self._load()
        self._validate()
        self._normalize()

    # ---------- loading & validation ----------

    def _load(self) -> None:
        try:
            raw = json.loads(self.policy_path.read_text())

            self.schema_ref = raw.get("$schema")
            if not self.schema_ref:
                raise PolicyError("Policy file missing $schema field")

            raw.pop("$schema", None)
            self.rules = raw

            del raw
        except Exception as e:
            raise PolicyError(f"Failed to load policy: {e}") from e

    def _validate(self) -> None:
        try:
            schema = _load_schema(self.schema_ref, self.policy_path)
            validate(instance=self.rules, schema=schema)
            del schema
        except ValidationError as e:
            raise PolicyError(f"Policy schema violation:\n{e.message}") from e
        except Exception as e:
            raise PolicyError(f"Schema validation failed: {e}") from e

    def _normalize(self) -> None:
        """
        Normalize rule values into sets for O(1) lookups
        """
        for rule in self.rules.values():
            rule["conflicts"] = set(rule.get("conflicts", []))
            rule["sub_mods"] = set(rule.get("sub_mods", []))

    # ---------- public API ----------

    def apply(self, mods: Iterable[str]) -> Set[str]:
        """
        Apply policy to a mod set.
        Recursively adds sub-mods and removes conflicts.
        Explicit mods always win over implicit ones.
        """
        explicit: Set[str] = set(mods)
        active: Set[str] = set(explicit)
        implicit: Set[str] = set()

        queue = deque(active)

        # 1. Expand sub-mods recursively
        while queue:
            current = queue.popleft()
            rule = self.rules.get(current)
            if not rule:
                continue

            for sub in rule["sub_mods"]:
                if sub not in active:
                    active.add(sub)
                    implicit.add(sub)
                    queue.append(sub)

        # 2. Resolve conflicts (implicit loses first)
        for mod in sorted(active):
            rule = self.rules.get(mod)
            if not rule:
                continue

            for conflict in rule["conflicts"]:
                if conflict in active:
                    if conflict in explicit and mod in explicit:
                        raise PolicyError(
                            f"Explicit mod conflict: {mod} ↔ {conflict}"
                        )

                    if conflict in implicit:
                        active.remove(conflict)
                        implicit.discard(conflict)

        del queue, explicit, implicit
        return active

    def diff(self, mods: Iterable[str]) -> Dict[str, List[str]]:
        """
        Show what would change without applying.
        """
        original = set(mods)
        final = self.apply(mods)

        diff = {
            "added": sorted(final - original),
            "removed": sorted(original - final),
        }

        del original, final
        return diff
