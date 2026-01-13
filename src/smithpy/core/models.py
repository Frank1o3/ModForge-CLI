from typing import List, Optional

from pydantic import BaseModel, Field


class Manifest(BaseModel):
    name: str
    minecraft: str
    loader: str
    mods: List[str] = []
    resourcepacks: List[str] = []
    shaderpacks: List[str] = []


class Hit(BaseModel):
    # Use Field to ensure default values work correctly during validation
    project_id: str = Field(default="")
    project_type: str = Field(default="")
    slug: str = Field(default="")
    categories: List[str] = Field(default_factory=list)
    versions: List[str] = Field(default_factory=list)

class SearchResult(BaseModel):
    # Optional list of Hit models
    hits: Optional[List[Hit]] = None