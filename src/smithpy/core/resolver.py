from typing import Iterable, List
from dataclasses import dataclass

from smithpy.core.policy import ModPolicy
from smithpy.api import ModrinthAPIConfig


@dataclass(frozen=True)
class ResolvedMod:
    slug: str
    project_id: str
    version_id: str
    download_url: str
    required: bool


class ModResolver:
    def __init__(
        self,
        *,
        policy: ModPolicy,
        api: ModrinthAPIConfig,
        mc_version: str,
        loader: str,
    ) -> None:
        self.policy = policy
        self.api = api
        self.mc_version = mc_version
        self.loader = loader

    def resolve(self, mods: Iterable[str]) -> List[ResolvedMod]:
        """
        Resolve mods and dependencies to exact Modrinth versions.
        No downloads. No file I/O.
        """
        # step one apply the policy expansion
        expanded = self.policy.apply(mods)
        resolved: List[ResolvedMod] = []
        
        for slug in expanded:
            # TODO:
            # - search project
            # - select compatible version
            # - collect dependencies
            pass

        return resolved