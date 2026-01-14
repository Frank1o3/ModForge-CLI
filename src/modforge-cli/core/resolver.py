from typing import Iterable, Set
from collections import deque

from modforge_cli.core.policy import ModPolicy
from modforge_cli.core.models import SearchResult, ProjectVersionList, ProjectVersion
from modforge_cli.api import ModrinthAPIConfig
from requests import get


try:
    from modforge_cli.__version__ import __version__, __author__
except ImportError:
    __version__ = "unknown"
    __author__ = "Frank1o3"


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

        self._headers = {
            "User-Agent": f"{__author__}/ModForge-CLI/{__version__}"
        }

    def _select_version(self, versions: list[ProjectVersion]) -> ProjectVersion | None:
        """
        Prefer:
        1. Release versions
        2. Matching MC + loader
        """
        for v in versions:
            if (
                v.is_release
                and self.mc_version in v.game_versions
                and self.loader in v.loaders
            ):
                return v

        for v in versions:
            if (
                self.mc_version in v.game_versions
                and self.loader in v.loaders
            ):
                return v

        return None

    def resolve(self, mods: Iterable[str]) -> Set[str]:
        expanded = self.policy.apply(mods)

        resolved: Set[str] = set()
        queue: deque[str] = deque()

        search_cache: dict[str, str | None] = {}
        version_cache: dict[str, list[ProjectVersion]] = {}

        # ---- Phase 1: slug → project_id ----
        for slug in expanded:
            if slug not in search_cache:
                url = self.api.search(
                    slug,
                    game_versions=[self.mc_version],
                    loaders=[self.loader],
                )
                response = get(url, headers=self._headers)
                data = SearchResult.model_validate_json(response.text)

                project_id = None
                for hit in data.hits:
                    if hit.project_type != "mod":
                        continue
                    if self.mc_version not in hit.versions:
                        continue
                    project_id = hit.project_id
                    break

                search_cache[slug] = project_id
                del url, response, data

            project_id = search_cache[slug]
            if project_id and project_id not in resolved:
                resolved.add(project_id)
                queue.append(project_id)

        # ---- Phase 2: dependency resolution ----
        while queue:
            pid = queue.popleft()

            if pid not in version_cache:
                url = self.api.project_versions(pid)
                response = get(url, headers=self._headers)
                versions = ProjectVersionList.validate_json(response.text)
                version_cache[pid] = versions
                del url, response
            else:
                versions = version_cache[pid]

            version = self._select_version(versions)
            if not version:
                continue

            for dep in version.dependencies:
                dtype = dep.dependency_type
                dep_id = dep.project_id

                if not dep_id:
                    continue

                if dtype == "incompatible":
                    raise RuntimeError(
                        f"Incompatible dependency detected: {pid} ↔ {dep_id}"
                    )

                if dtype in ("required", "optional"):
                    if dep_id not in resolved:
                        resolved.add(dep_id)
                        queue.append(dep_id)

                # embedded deps are intentionally ignored

            del versions, version, pid

        del queue, expanded, search_cache, version_cache
        return resolved
