from typing import List
from pathlib import Path

from api import ModrinthAPIConfig
from .policy import ModPolicy

def get_project_root(start: Path) -> Path:
    for parent in start.resolve().parents:
        if parent.name == "src":
            return parent.parent
    raise RuntimeError("Could not locate project root (missing src directory)")

script_path = get_project_root(Path(__file__))


modrinth_api_path = script_path / "configs" / "modrinth_api.json"
policy_path = script_path / "configs" / "policy.json"

api = ModrinthAPIConfig(modrinth_api_path)
policy = ModPolicy(policy_path)

def run(name:str, loader:str, version:str, mods: List[str]) -> None:
    mod = policy.apply(mods)
    print(mod)
