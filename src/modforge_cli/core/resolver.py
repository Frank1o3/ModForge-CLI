import asyncio
from collections import deque
from collections.abc import Iterable

import aiohttp

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core.models import ProjectVersion, ProjectVersionList, SearchResult
from modforge_cli.core.policy import ModPolicy

try:
    from modforge_cli.__version__ import __author__, __version__
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

        self._headers = {"User-Agent": f"{__author__}/ModForge-CLI/{__version__}"}

    def _select_version(self, versions: list[ProjectVersion]) -> ProjectVersion | None:
        """
        Prefer:
        1. Release versions
        2. Matching MC + loader
        """
        for v in versions:
            if v.is_release and self.mc_version in v.game_versions and self.loader in v.loaders:
                return v

        for v in versions:
            if self.mc_version in v.game_versions and self.loader in v.loaders:
                return v

        return None

    async def _search_project(self, slug: str, session: aiohttp.ClientSession) -> str | None:
        """Search for a project by slug and return its project_id"""
        url = self.api.search(
            slug,
            game_versions=[self.mc_version],
            loaders=[self.loader],
        )

        try:
            async with session.get(url) as response:
                data = SearchResult.model_validate_json(await response.text())

            for hit in data.hits:
                if hit.project_type != "mod":
                    continue
                if self.mc_version not in hit.versions:
                    continue
                return hit.project_id
        except Exception as e:
            print(f"Warning: Failed to search for '{slug}': {e}")

        return None

    async def _fetch_versions(
        self, project_id: str, session: aiohttp.ClientSession
    ) -> list[ProjectVersion]:
        """Fetch all versions for a project"""
        url = self.api.project_versions(project_id)

        try:
            async with session.get(url) as response:
                return ProjectVersionList.validate_json(await response.text())
        except Exception as e:
            print(f"Warning: Failed to fetch versions for '{project_id}': {e}")
            return []

    async def resolve(self, mods: Iterable[str], session: aiohttp.ClientSession) -> set[str]:
        """
        Asynchronously resolve all mod dependencies.

        Args:
            mods: Initial list of mod slugs
            session: Active aiohttp session

        Returns:
            Set of resolved project IDs
        """
        expanded = self.policy.apply(mods)

        resolved: set[str] = set()
        queue: deque[str] = deque()

        search_cache: dict[str, str | None] = {}
        version_cache: dict[str, list[ProjectVersion]] = {}

        # ---- Phase 1: slug → project_id (parallel) ----
        search_tasks = []
        slugs_to_search = []

        for slug in expanded:
            if slug not in search_cache:
                slugs_to_search.append(slug)
                search_tasks.append(self._search_project(slug, session))

        if search_tasks:
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for slug, result in zip(slugs_to_search, search_results):
                if isinstance(result, Exception):
                    print(f"Error searching for '{slug}': {result}")
                    search_cache[slug] = None
                else:
                    search_cache[slug] = result

        # Add found projects to queue
        for slug in expanded:
            project_id = search_cache.get(slug)
            if project_id and project_id not in resolved:
                resolved.add(project_id)
                queue.append(project_id)

        # ---- Phase 2: dependency resolution (batched) ----
        BATCH_SIZE = 10

        while queue:
            # Process in batches to avoid overwhelming the API
            batch = []
            for _ in range(min(len(queue), BATCH_SIZE)):
                if queue:
                    batch.append(queue.popleft())

            # Fetch versions for batch in parallel
            version_tasks = []
            projects_to_fetch = []

            for pid in batch:
                if pid not in version_cache:
                    projects_to_fetch.append(pid)
                    version_tasks.append(self._fetch_versions(pid, session))

            if version_tasks:
                version_results = await asyncio.gather(*version_tasks, return_exceptions=True)

                for pid, result in zip(projects_to_fetch, version_results, strict=False):
                    if isinstance(result, Exception):
                        print(f"Error fetching versions for '{pid}': {result}")
                        version_cache[pid] = []
                    else:
                        version_cache[pid] = result

            # Process dependencies
            for pid in batch:
                versions = version_cache.get(pid, [])
                version = self._select_version(versions)

                if not version:
                    print(f"Warning: No compatible version found for '{pid}'")
                    continue

                for dep in version.dependencies:
                    dtype = dep.dependency_type
                    dep_id = dep.project_id

                    if not dep_id:
                        continue

                    if dtype == "incompatible" and dep_id in resolved:
                        resolved.remove(dep_id)
                        print(
                            f"Warning: Removed incompatible dependency '{dep_id}' "
                            f"(conflicts with '{pid}') — it may have been added earlier."
                        )

                    if dtype in ("required", "optional") and dep_id not in resolved:
                        resolved.add(dep_id)
                        queue.append(dep_id)

        del queue, expanded, search_cache, version_cache
        return resolved
