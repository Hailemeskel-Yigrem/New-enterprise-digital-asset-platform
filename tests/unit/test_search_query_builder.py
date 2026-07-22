"""Unit tests for SearchQueryBuilder."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import utc_now
from vaultforge.infrastructure.search.query_builder import (
    BoolQuery,
    FieldFilter,
    FilterOperator,
    MatchMode,
    SearchQuery,
    SearchQueryBuilder,
    SortOrder,
    TermQuery,
)


def test_build_simple_query() -> None:
    builder = SearchQueryBuilder()
    org_id = uuid.uuid4()
    built = builder.build_simple(org_id, "contract renewal")
    assert built.organization_id == str(org_id)
    assert built.must_clauses
    assert built.pagination["limit"] == 25


def test_build_with_filters() -> None:
    builder = SearchQueryBuilder()
    org_id = uuid.uuid4()
    built = builder.build_filtered(
        org_id,
        "invoice",
        resource_types=["document"],
        tags=["finance"],
        limit=10,
    )
    assert built.pagination["limit"] == 10
    assert any("resource_type" in str(f) for f in built.filters)


def test_bool_query_compilation() -> None:
    builder = SearchQueryBuilder()
    org_id = uuid.uuid4()
    query = SearchQuery(
        organization_id=org_id,
        bool_query=BoolQuery(
            must=[TermQuery(field="title", value="policy", mode=MatchMode.PHRASE)],
            should=[TermQuery(field="body", value="compliance")],
        ),
    )
    built = builder.build(query)
    assert built.must_clauses
    assert built.should_clauses


def test_invalid_limit_raises() -> None:
    builder = SearchQueryBuilder()
    with pytest.raises(ValidationError):
        builder.build(SearchQuery(organization_id=uuid.uuid4(), limit=0))


def test_date_range_validation() -> None:
    builder = SearchQueryBuilder()
    now = utc_now()
    with pytest.raises(ValidationError):
        builder.build(
            SearchQuery(
                organization_id=uuid.uuid4(),
                date_from=now,
                date_to=now - timedelta(days=1),
            )
        )


def test_field_filter_between() -> None:
    builder = SearchQueryBuilder()
    org_id = uuid.uuid4()
    query = SearchQuery(
        organization_id=org_id,
        filters=[
            FieldFilter(
                field_name="size_bytes", operator=FilterOperator.BETWEEN, values=[100, 5000]
            )
        ],
    )
    built = builder.build(query)
    assert built.filters


def test_elasticsearch_body() -> None:
    builder = SearchQueryBuilder()
    built = builder.build_simple(uuid.uuid4(), "test")
    body = builder.to_elasticsearch_body(built)
    assert "query" in body
    assert "sort" in body


def test_explain_score() -> None:
    builder = SearchQueryBuilder()
    built = builder.build_simple(uuid.uuid4(), "alpha")
    explanation = builder.explain_score(built)
    assert explanation["query_text"] == "alpha"


def test_sort_orders() -> None:
    builder = SearchQueryBuilder()
    org_id = uuid.uuid4()
    for sort in (SortOrder.RELEVANCE, SortOrder.TITLE_ASC, SortOrder.UPDATED_DESC):
        built = builder.build(SearchQuery(organization_id=org_id, sort=sort))
        assert built.sort
