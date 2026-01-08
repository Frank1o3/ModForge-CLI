from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, TypedDict
from urllib.request import urlopen

from jsonschema import ValidationError, validate

class NormalizedModRule(TypedDict):
    conflicts: Set[str]
    sub_mods: Set[str]

NormalizedPolicyRules = Dict[str, NormalizedModRule]

class PolicyError(RuntimeError):
    pass


class ModPolicy:
    """
    Enforces mod compatibility rules:
    - removes conflicts
    - injects recommended sub-mods
    """

    SCHEMA_URL = (
        "https://frank1o3.github.io/smithpy/schemas/policy.schema.json"
    )

    def __init__(self, policy_path: Path):
        self.policy_path = policy_path
        self.rules: NormalizedPolicyRules = {}

        self._load()
        self._validate()
        self._normalize()

    # ---------- loading & validation ----------

    def _load(self) -> None:
        try:
            data = json.loads(self.policy_path.read_text())

            # Strip schema metadata – not part of runtime rules
            data.pop("$schema", None)

            self.rules = data
        except Exception as e:
            raise PolicyError(f"Failed to load policy: {e}") from e


    def _validate(self) -> None:
        try:
            with urlopen(self.SCHEMA_URL) as resp:
                schema = json.load(resp)
            validate(instance=self.rules, schema=schema)
        except ValidationError as e:
            raise PolicyError(f"Policy schema violation:\n{e.message}") from e
        except Exception as e:
            raise PolicyError(f"Schema validation failed: {e}") from e

    def _normalize(self) -> None:
        """
        Ensure all values are sets for O(1) lookups
        """
        for _, rule in self.rules.items():
            rule["conflicts"] = set(rule.get("conflicts", []))
            rule["sub_mods"] = set(rule.get("sub_mods", []))

    # ---------- public API ----------
    def apply(self, mods: Iterable[str]) -> Set[str]:
        """
        Apply policy to a mod set.
        Recursively adds sub-mods and removes conflicts.
        User-selected mods always take priority over sub-mods.
        """
        explicit: Set[str] = set(mods)
        active: Set[str] = set(explicit)
        implicit: Set[str] = set()

        # 1. Expand sub-mods recursively
        to_process = list(active)
        while to_process:
            current = to_process.pop(0)
            rule = self.rules.get(current)
            if not rule:
                continue

            for sub in rule["sub_mods"]:
                if sub not in active:
                    active.add(sub)
                    implicit.add(sub)
                    to_process.append(sub)

        # 2. Remove conflicts (implicit mods lose first)
        for mod in list(active):
            rule = self.rules.get(mod)
            if not rule:
                continue

            for conflict in rule["conflicts"]:
                if conflict in active:
                    # Only remove implicit mods
                    if conflict in implicit:
                        active.remove(conflict)
                        implicit.discard(conflict)

        return active


    def diff(self, mods: Iterable[str]) -> Dict[str, List[str]]:
        """
        Show what would change without applying.
        """
        original = set(mods)
        final = self.apply(mods)

        return {
            "added": sorted(final - original),
            "removed": sorted(original - final),
        }
