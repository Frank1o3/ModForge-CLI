import asyncio
from collections import deque
from collections.abc import Iterable
from typing import Any

import aiohttp
from rich.console import Console

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core.models import Hit, ProjectVersion, ProjectVersionList, SearchResult
from modforge_cli.core.policy import ModPolicy
from modforge_cli.core.utils import calculate_match_score

console = Console()

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
        include_optional_deps: bool = False,
    ) -> None:
        self.policy = policy
        self.api = api
        self.mc_version = mc_version
        self.loader = loader
        self.include_optional_deps = include_optional_deps

        self._headers = {"User-Agent": f"{__author__}/ModForge-CLI/{__version__}"}

    def _select_version(self, versions: list[ProjectVersion]) -> ProjectVersion | None:
        """
        Select the best version for the target MC version and loader.

        Priority:
        1. Release versions matching MC + loader (newest first)
        2. Any version matching MC + loader (newest first)
        """
        version_priority = {"release": 3, "beta": 2, "alpha": 1}

        def version_score(v: ProjectVersion) -> tuple[int, str]:
            vtype = version_priority.get(v.version_type, 0)
            # Use date_published for chronological ordering (ISO 8601, sortable)
            vdate = v.date_published or ""
            return (vtype, vdate)

        # Filter compatible versions
        compatible = [
            v for v in versions
            if self.mc_version in v.game_versions and self.loader in v.loaders
        ]

        if not compatible:
            return None

        # Sort by version type (release > beta > alpha), then by date (newest first)
        compatible.sort(key=version_score, reverse=True)
        return compatible[0]

    async def _search_project(self, slug: str, session: aiohttp.ClientSession) -> str | None:
        """
        Search for a project by slug and return its project_id.

        Uses fuzzy matching to find the best hit (same scoring as 'add' command).
        Returns None if no suitable match is found.
        """
        url = self.api.search(
            slug,
            game_versions=[self.mc_version],
            loaders=[self.loader],
            project_type="mod",
        )

        try:
            async with session.get(url) as response:
                data = SearchResult.model_validate_json(await response.text())

            if not data.hits:
                return None

            # Find best matching hit using the same scoring as 'add' command
            best_hit: Hit | None = None
            best_score = 0

            for hit in data.hits:
                if hit.project_type != "mod":
                    continue
                if self.mc_version not in hit.versions:
                    continue

                score = calculate_match_score(slug, hit.slug, getattr(hit, "title", ""))
                if score > best_score:
                    best_score = score
                    best_hit = hit

            # Only accept high-confidence matches (score >= 80)
            if best_hit and best_score >= 80:
                return best_hit.project_id

            # Fallback: if exact slug match (score 100), accept regardless
            for hit in data.hits:
                if hit.project_type != "mod":
                    continue
                if hit.slug == slug:
                    return hit.project_id

            return None

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to search for '{slug}': {e}[/yellow]")
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
            console.print(f"[yellow]Warning: Failed to fetch versions for '{project_id}': {e}[/yellow]")
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

        search_cache: dict[str, Any] = {}
        version_cache: dict[str, list[ProjectVersion]] = {}
        failed_slugs: list[str] = []

        # ---- Phase 1: slug → project_id (parallel) ----
        search_tasks = []
        slugs_to_search = []

        for slug in expanded:
            if slug not in search_cache:
                slugs_to_search.append(slug)
                search_tasks.append(self._search_project(slug, session))

        if search_tasks:
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for slug, result in zip(slugs_to_search, search_results, strict=False):
                if isinstance(result, Exception):
                    console.print(f"[red]Error searching for '{slug}': {result}[/red]")
                    failed_slugs.append(slug)
                elif result is None:
                    failed_slugs.append(slug)
                    search_cache[slug] = None
                else:
                    search_cache[slug] = str(result)

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

                for pid, ver_result in zip(projects_to_fetch, version_results, strict=False):
                    if isinstance(ver_result, Exception):
                        console.print(f"[red]Error fetching versions for '{pid}': {ver_result}[/red]")
                        version_cache[pid] = []
                    elif isinstance(ver_result, list):
                        version_cache[pid] = ver_result

            # Process dependencies
            for pid in batch:
                versions = version_cache.get(pid, [])
                version = self._select_version(versions)

                if not version:
                    console.print(f"[yellow]Warning: No compatible version found for '{pid}'[/yellow]")
                    continue

                for dep in version.dependencies:
                    dtype = dep.dependency_type
                    dep_id = dep.project_id

                    if not dep_id:
                        continue

                    if dtype == "incompatible" and dep_id in resolved:
                        resolved.remove(dep_id)
                        console.print(
                            f"[yellow]Warning: Removed incompatible dependency '{dep_id}' "
                            f"(conflicts with '{pid}')[/yellow]"
                        )

                    if dtype == "required" and dep_id not in resolved:
                        resolved.add(dep_id)
                        queue.append(dep_id)
                    elif dtype == "optional" and self.include_optional_deps and dep_id not in resolved:
                        resolved.add(dep_id)
                        queue.append(dep_id)
                        console.print(f"[dim]  + Optional dep added: {dep_id}[/dim]")

        # Report failed slugs
        if failed_slugs:
            console.print(f"\n[yellow]Warning: {len(failed_slugs)} mod(s) could not be resolved:[/yellow]")
            for slug in failed_slugs:
                console.print(f"  - {slug}")
            console.print("[dim]Check the slugs or try searching on https://modrinth.com[/dim]\n")

        del queue, expanded, search_cache, version_cache, failed_slugs
        return resolved
