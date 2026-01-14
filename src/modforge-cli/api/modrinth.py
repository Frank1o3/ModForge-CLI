"""
api/modrith_api.py - Modrinth API v2 URL builder using modrinth_api.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


class ModrinthAPIConfig:
    """Loads modrinth_api.json and builds Modrinth API URLs."""

    def __init__(self, config_path: str | Path = "configs/modrinth_api.json"):
        self.config_path = config_path if isinstance(config_path, Path) else Path(config_path)
        self.base_url: str = ""
        self.endpoints: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Modrinth API config not found: {self.config_path}"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.base_url = data.get("BASE_URL", "").rstrip("/")
        if not self.base_url:
            raise ValueError("BASE_URL missing in modrinth_api.json")

        self.endpoints = data.get("ENDPOINTS", {})
        if not isinstance(self.endpoints, Dict):
            raise ValueError("ENDPOINTS section is invalid")

    def build_url(self, template: str, **kwargs: str) -> str:
        """Format a template string with kwargs and prepend base URL."""
        try:
            path = template.format(**kwargs)
            return f"{self.base_url}{path}"
        except KeyError as e:
            raise ValueError(f"Missing URL parameter: {e}")

    # === Search ===

    def search(
        self,
        query: Optional[str] = None,
        facets: Optional[List[List[str]] | str] = None,
        categories: Optional[List[str]] = None,
        loaders: Optional[List[str]] = None,
        game_versions: Optional[List[str]] = None,
        license_: Optional[str] = None,
        project_type: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = 10,
        index: Optional[str] = "relevance",
    ) -> str:
        """
        Build the Modrinth search URL with query parameters.

        Docs: https://docs.modrinth.com/api-spec#endpoints-search

        Facets format: [[inner AND], [inner AND]] = outer OR
        Example: [["categories:performance"], ["project_type:mod"]]

        Args:
            query: Search term (e.g., "sodium")
            facets: Advanced filters as list of lists or JSON string
            categories: Filter by categories (e.g., ["performance"])
            loaders: Filter by loaders (e.g., ["fabric", "quilt"])
            game_versions: Filter by Minecraft versions (e.g., ["1.21.1"])
            license_: Filter by license (e.g., "MIT")
            project_type: "mod", "resourcepack", "shader", "modpack", "datapack"
            offset: Pagination offset
            limit: Results per page (max 100)
            index: Sort by "relevance", "downloads", "updated", "newest"

        Returns:
            Full search URL with query parameters
        """
        base = self.build_url(self.endpoints["search"])
        params = []
        if query:
            params.append(f"query={quote_plus(query)}")

        facets_array = []
        if facets:
            if isinstance(facets, str):
                params.append(f"facets={quote_plus(facets)}")
            else:
                facets_array.extend(facets)

        if project_type:
            facets_array.append([f"project_type:{project_type}"])
        if categories:
            [facets_array.append([f"categories:{c}"]) for c in categories]
        if loaders:
            facets_array.append([f"categories:{l}" for l in loaders])
        if game_versions:
            facets_array.append([f"versions:{v}" for v in game_versions])
        if license_:
            facets_array.append([f"license:{license_}"])

        if facets_array and not (isinstance(facets, str)):
            params.append(f"facets={quote_plus(json.dumps(facets_array))}")

        if offset is not None:
            params.append(f"offset={offset}")
        if limit is not None:
            params.append(f"limit={min(limit, 100)}")
        if index:
            params.append(f"index={index}")

        return f"{base}?{'&'.join(params)}" if params else base

    # === Projects ===

    def project(self, project_id: str) -> str:
        return self.build_url(self.endpoints["projects"]["project"], id=project_id)

    def project_versions(self, project_id: str) -> str:
        return self.build_url(
            self.endpoints["projects"]["project_versions"], id=project_id
        )

    def project_dependencies(self, project_id: str) -> str:
        return self.build_url(self.endpoints["projects"]["dependencies"], id=project_id)

    def project_gallery(self, project_id: str) -> str:
        return self.build_url(self.endpoints["projects"]["gallery"], id=project_id)

    def project_icon(self, project_id: str) -> str:
        return self.build_url(self.endpoints["projects"]["icon"], id=project_id)

    def check_following(self, project_id: str) -> str:
        return self.build_url(
            self.endpoints["projects"]["check_following"], id=project_id
        )

    # === Versions ===

    def version(self, version_id: str) -> str:
        return self.build_url(self.endpoints["versions"]["version"], id=version_id)

    def version_files(self, version_id: str) -> str:
        return self.build_url(self.endpoints["versions"]["files"], id=version_id)

    def version_file_download(self, version_id: str, filename: str) -> str:
        return self.build_url(
            self.endpoints["versions"]["download"], id=version_id, filename=filename
        )

    def file_by_hash(self, hash_: str) -> str:
        return self.build_url(self.endpoints["versions"]["file_by_hash"], hash=hash_)

    def versions_by_hash(self, hash_: str) -> str:
        return self.build_url(
            self.endpoints["versions"]["versions_by_hash"], hash=hash_
        )

    def latest_version_for_hash(self, hash_: str, algorithm: str = "sha1") -> str:
        return self.build_url(
            self.endpoints["versions"]["latest_for_hash"], hash=hash_, algo=algorithm
        )

    # === Tags ===

    def categories(self) -> str:
        return self.build_url(self.endpoints["tags"]["categories"])

    def loaders(self) -> str:
        return self.build_url(self.endpoints["tags"]["loaders"])

    def game_versions(self) -> str:
        return self.build_url(self.endpoints["tags"]["game_versions"])

    def licenses(self) -> str:
        return self.build_url(self.endpoints["tags"]["licenses"])

    def environments(self) -> str:
        return self.build_url(self.endpoints["tags"]["environments"])

    # === Teams ===

    def team(self, team_id: str) -> str:
        return self.build_url(self.endpoints["teams"]["team"], id=team_id)

    def team_members(self, team_id: str) -> str:
        return self.build_url(self.endpoints["teams"]["members"], id=team_id)

    # === User ===

    def user(self, user_id: str) -> str:
        return self.build_url(self.endpoints["user"]["user"], id=user_id)

    def user_projects(self, user_id: str) -> str:
        return self.build_url(self.endpoints["user"]["user_projects"], id=user_id)

    def user_notifications(self, user_id: str) -> str:
        return self.build_url(self.endpoints["user"]["notifications"], id=user_id)

    def user_avatar(self, user_id: str) -> str:
        return self.build_url(self.endpoints["user"]["avatar"], id=user_id)

    # === Bulk ===

    def bulk_projects(self) -> str:
        return self.build_url(self.endpoints["bulk"]["projects"])

    def bulk_versions(self) -> str:
        return self.build_url(self.endpoints["bulk"]["versions"])

    def bulk_version_files(self) -> str:
        return self.build_url(self.endpoints["bulk"]["version_files"])
