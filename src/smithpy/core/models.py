from typing import List, Dict, Literal
from pydantic import BaseModel, Field, TypeAdapter


class BaseAPIModel(BaseModel):
    model_config = {"extra": "ignore"}


class Manifest(BaseModel):
    name: str
    minecraft: str
    loader: str
    loader_version: str | None = None
    mods: List[str] = Field(default_factory=list)
    resourcepacks: List[str] = Field(default_factory=list)
    shaderpacks: List[str] = Field(default_factory=list)


class Hit(BaseAPIModel):
    project_id: str
    project_type: str
    slug: str
    categories: List[str] = Field(default_factory=list)
    versions: List[str] = Field(default_factory=list)


class SearchResult(BaseAPIModel):
    hits: List[Hit] = Field(default_factory=list)


class Dependency(BaseAPIModel):
    dependency_type: (
        Literal["required", "optional", "incompatible", "embedded"] | None
    ) = None
    file_name: str | None = None
    project_id: str | None = None
    version_id: str | None = None


class File(BaseAPIModel):
    id: str | None = None
    hashes: Dict[str, str] = Field(default_factory=dict)
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
    dependencies: List[Dependency] = Field(default_factory=list)
    files: List[File] = Field(default_factory=list)
    game_versions: List[str] = Field(default_factory=list)
    loaders: List[str] = Field(default_factory=list)

    @property
    def is_release(self) -> bool:
        return self.version_type == "release"


ProjectVersionList = TypeAdapter(List[ProjectVersion])

__all__ = [
    "Manifest",
    "SearchResult",
    "ProjectVersion",
    "ProjectVersionList",
]
