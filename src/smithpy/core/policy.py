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
        """
        active: Set[str] = set(mods)
        
        # 1. Expand sub-mods recursively
        # We use a queue to ensure we check the rules for every newly added mod
        to_process = list(active)
        while to_process:
            current_mod = to_process.pop(0)
            rule = self.rules.get(current_mod)
            
            if rule and "sub_mods" in rule:
                for sub in rule["sub_mods"]:
                    if sub not in active:
                        active.add(sub)
                        # Add the new mod to the queue so its own sub-mods are checked
                        to_process.append(sub)

        # 2. Remove conflicts
        # After all possible mods are added, we filter out conflicts
        final_mods = active.copy()
        for mod in active:
            rule = self.rules.get(mod)
            if rule and "conflicts" in rule:
                for conflict in rule["conflicts"]:
                    if conflict in final_mods:
                        final_mods.remove(conflict)

        return final_mods

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
