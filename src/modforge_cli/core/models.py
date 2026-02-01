from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter


class BaseAPIModel(BaseModel):
    model_config = {"extra": "ignore"}


class Mod(BaseModel):
    id: str
    side: Literal["server", "client", "both"]
    required: bool = False

    @property
    def is_server_side(self) -> bool:
        return self.side == "server"
    @property
    def is_client_side(self) -> bool:
        return self.side == "client"
    @property
    def is_both_side(self) -> bool:
        return self.side == "both"

class Manifest(BaseModel):
    name: str
    minecraft: str
    loader: str
    loader_version: str | None = None
    mods: list[str] = Field(default_factory=list)
    resourcepacks: list[str] = Field(default_factory=list)
    shaderpacks: list[str] = Field(default_factory=list)


class Hit(BaseAPIModel):
    project_id: str
    project_type: str
    slug: str
    categories: list[str] = Field(default_factory=list)
    versions: list[str] = Field(default_factory=list)


class SearchResult(BaseAPIModel):
    hits: list[Hit] = Field(default_factory=list)


class Dependency(BaseAPIModel):
    dependency_type: Literal["required", "optional", "incompatible", "embedded"] | None = None
    file_name: str | None = None
    project_id: str | None = None
    version_id: str | None = None


class File(BaseAPIModel):
    id: str | None = None
    hashes: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    filename: str | None = None
    primary: bool | None = None
    size: int | None = None
    file_type: str | None = None


class ProjectVersion(BaseAPIModel):
    id: str
    project_id: str
    version_number: str
    version_type: str
    dependencies: list[Dependency] = Field(default_factory=list)
    files: list[File] = Field(default_factory=list)
    game_versions: list[str] = Field(default_factory=list)
    loaders: list[str] = Field(default_factory=list)

    @property
    def is_release(self) -> bool:
        return self.version_type == "release"


ProjectVersionList = TypeAdapter(list[ProjectVersion])

__all__ = ["Manifest", "SearchResult", "ProjectVersion", "ProjectVersionList"]
