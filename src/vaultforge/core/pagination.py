"""Pagination helpers for list endpoints and repository queries."""

from __future__ import annotations

import math
from typing import Generic, Self, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class PageParams(BaseModel):
    """Offset-based pagination parameters with sane defaults."""

    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(default=50, ge=1, le=200, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    @classmethod
    def from_limit_offset(cls, *, limit: int, offset: int) -> PageParams:
        page_size = max(1, min(limit, 200))
        page = (max(offset, 0) // page_size) + 1
        return cls(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    """Paginated response envelope."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def compute_pages(self) -> Self:
        if self.page_size <= 0:
            self.pages = 0
        elif self.total:
            self.pages = math.ceil(self.total / self.page_size)
        else:
            self.pages = 0
        return self

    @classmethod
    def build(cls, items: list[T], *, total: int, params: PageParams) -> Page[T]:
        pages = math.ceil(total / params.page_size) if total else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )
