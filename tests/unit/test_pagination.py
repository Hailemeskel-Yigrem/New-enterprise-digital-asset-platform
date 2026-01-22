"""Unit tests for pagination helpers."""

from __future__ import annotations

import math

import pytest

from vaultforge.core.pagination import Page, PageParams


def test_page_params_offset_and_limit() -> None:
    params = PageParams(page=3, page_size=20)
    assert params.offset == 40
    assert params.limit == 20


def test_page_params_from_limit_offset() -> None:
    params = PageParams.from_limit_offset(limit=50, offset=100)
    assert params.page == 3
    assert params.page_size == 50


@pytest.mark.parametrize(
    ("total", "page_size", "expected_pages"),
    [
        (0, 10, 0),
        (1, 10, 1),
        (25, 10, 3),
        (100, 25, 4),
    ],
)
def test_page_build_computes_pages(total: int, page_size: int, expected_pages: int) -> None:
    params = PageParams(page=1, page_size=page_size)
    page = Page.build(list(range(min(total, page_size))), total=total, params=params)
    assert page.pages == expected_pages
    assert page.total == total
    assert page.page_size == page_size


def test_page_validator_computes_pages_on_construct() -> None:
    page = Page(items=["a", "b"], total=10, page=1, page_size=4, pages=0)
    assert page.pages == math.ceil(10 / 4)


def test_page_build_empty_result() -> None:
    params = PageParams(page=1, page_size=10)
    page = Page.build([], total=0, params=params)
    assert page.items == []
    assert page.total == 0
    assert page.pages == 0


def test_page_params_caps_page_size_via_from_limit_offset() -> None:
    params = PageParams.from_limit_offset(limit=500, offset=0)
    assert params.page_size == 200
