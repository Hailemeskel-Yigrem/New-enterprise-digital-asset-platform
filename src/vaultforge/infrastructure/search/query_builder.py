"""Full-text search query builder with composable DSL."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from vaultforge.core.exceptions import ValidationError


class QueryOperator(StrEnum):
    AND = "and"
    OR = "or"
    NOT = "not"


class MatchMode(StrEnum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    PREFIX = "prefix"
    PHRASE = "phrase"
    WILDCARD = "wildcard"


class SortOrder(StrEnum):
    RELEVANCE = "relevance"
    UPDATED_DESC = "updated_desc"
    UPDATED_ASC = "updated_asc"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"
    CREATED_DESC = "created_desc"


class FilterOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    EXISTS = "exists"


@dataclass(slots=True)
class FieldFilter:
    field_name: str
    operator: FilterOperator
    value: Any = None
    values: list[Any] = field(default_factory=list)

    def validate(self) -> None:
        if not self.field_name.strip():
            raise ValidationError("Filter field is required")
        if self.operator == FilterOperator.BETWEEN and len(self.values) != 2:
            raise ValidationError("BETWEEN filter requires exactly two values")
        if self.operator == FilterOperator.IN and not self.values:
            raise ValidationError("IN filter requires values list")


@dataclass(slots=True)
class TermQuery:
    field: str
    value: str
    mode: MatchMode = MatchMode.FUZZY
    boost: float = 1.0

    def validate(self) -> None:
        if not self.field.strip():
            raise ValidationError("Term query field is required")
        if not self.value.strip():
            raise ValidationError("Term query value is required")
        if self.boost <= 0:
            raise ValidationError("Boost must be positive")


@dataclass(slots=True)
class BoolQuery:
    must: list[TermQuery | Self] = field(default_factory=list)
    should: list[TermQuery | Self] = field(default_factory=list)
    must_not: list[TermQuery | Self] = field(default_factory=list)
    minimum_should_match: int = 0

    def validate(self) -> None:
        for clause in (*self.must, *self.should, *self.must_not):
            if isinstance(clause, TermQuery):
                clause.validate()
            else:
                clause.validate()
        if self.should and self.minimum_should_match < 0:
            raise ValidationError("minimum_should_match cannot be negative")


@dataclass(slots=True)
class HighlightConfig:
    enabled: bool = True
    fields: list[str] = field(default_factory=lambda: ["title", "body"])
    fragment_size: int = 150
    max_fragments: int = 3
    pre_tag: str = "<em>"
    post_tag: str = "</em>"


@dataclass(slots=True)
class FacetRequest:
    field: str
    size: int = 10
    min_count: int = 1

    def validate(self) -> None:
        if not self.field.strip():
            raise ValidationError("Facet field is required")
        if self.size < 1:
            raise ValidationError("Facet size must be positive")


@dataclass(slots=True)
class SearchQuery:
    organization_id: uuid.UUID
    query_text: str = ""
    bool_query: BoolQuery | None = None
    filters: list[FieldFilter] = field(default_factory=list)
    facets: list[FacetRequest] = field(default_factory=list)
    resource_types: list[str] = field(default_factory=list)
    folder_ids: list[uuid.UUID] = field(default_factory=list)
    author_ids: list[uuid.UUID] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort: SortOrder = SortOrder.RELEVANCE
    limit: int = 25
    offset: int = 0
    highlight: HighlightConfig = field(default_factory=HighlightConfig)

    def validate(self) -> None:
        if self.limit < 1 or self.limit > 200:
            raise ValidationError("limit must be between 1 and 200")
        if self.offset < 0:
            raise ValidationError("offset cannot be negative")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError("date_from cannot be after date_to")
        for f in self.filters:
            f.validate()
        for facet in self.facets:
            facet.validate()
        if self.bool_query:
            self.bool_query.validate()


@dataclass(slots=True)
class BuiltQuery:
    """Serialized query representation for search backends."""

    organization_id: str
    must_clauses: list[dict[str, Any]]
    should_clauses: list[dict[str, Any]]
    must_not_clauses: list[dict[str, Any]]
    filters: list[dict[str, Any]]
    facets: list[dict[str, Any]]
    sort: list[dict[str, str]]
    pagination: dict[str, int]
    highlight: dict[str, Any] | None
    raw_query_text: str


class SearchQueryBuilder:
    """Build backend-agnostic search queries from domain SearchQuery objects."""

    DEFAULT_SEARCH_FIELDS = ("title", "body", "filename", "tags", "folder_path")

    def __init__(self, search_fields: tuple[str, ...] | None = None) -> None:
        self.search_fields = search_fields or self.DEFAULT_SEARCH_FIELDS

    def build(self, query: SearchQuery) -> BuiltQuery:
        query.validate()
        must: list[dict[str, Any]] = []
        should: list[dict[str, Any]] = []
        must_not: list[dict[str, Any]] = []

        if query.query_text.strip():
            must.append(self._multi_match(query.query_text.strip()))

        if query.bool_query:
            compiled = self._compile_bool(query.bool_query)
            must.extend(compiled["must"])
            should.extend(compiled["should"])
            must_not.extend(compiled["must_not"])

        filters = self._build_filters(query)
        facets = [self._build_facet(f) for f in query.facets]
        sort = self._build_sort(query.sort)
        highlight = self._build_highlight(query.highlight) if query.highlight.enabled else None

        return BuiltQuery(
            organization_id=str(query.organization_id),
            must_clauses=must,
            should_clauses=should,
            must_not_clauses=must_not,
            filters=filters,
            facets=facets,
            sort=sort,
            pagination={"limit": query.limit, "offset": query.offset},
            highlight=highlight,
            raw_query_text=query.query_text,
        )

    def build_simple(
        self,
        organization_id: uuid.UUID,
        text: str,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> BuiltQuery:
        return self.build(
            SearchQuery(
                organization_id=organization_id,
                query_text=text,
                limit=limit,
                offset=offset,
            )
        )

    def build_filtered(
        self,
        organization_id: uuid.UUID,
        text: str,
        *,
        resource_types: list[str] | None = None,
        tags: list[str] | None = None,
        folder_ids: list[uuid.UUID] | None = None,
        limit: int = 25,
    ) -> BuiltQuery:
        return self.build(
            SearchQuery(
                organization_id=organization_id,
                query_text=text,
                resource_types=resource_types or [],
                tags=tags or [],
                folder_ids=folder_ids or [],
                limit=limit,
            )
        )

    def _multi_match(self, text: str) -> dict[str, Any]:
        return {
            "type": "multi_match",
            "query": text,
            "fields": [f"{field}^{self._field_boost(field)}" for field in self.search_fields],
            "operator": QueryOperator.AND.value,
            "fuzziness": "AUTO",
        }

    def _field_boost(self, field: str) -> float:
        boosts = {"title": 3.0, "filename": 2.5, "tags": 2.0, "folder_path": 1.2, "body": 1.0}
        return boosts.get(field, 1.0)

    def _compile_bool(self, bool_query: BoolQuery) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {"must": [], "should": [], "must_not": []}
        for term in bool_query.must:
            result["must"].append(self._compile_clause(term))
        for term in bool_query.should:
            result["should"].append(self._compile_clause(term))
        for term in bool_query.must_not:
            result["must_not"].append(self._compile_clause(term))
        if bool_query.should and bool_query.minimum_should_match:
            result["minimum_should_match"] = bool_query.minimum_should_match  # type: ignore[assignment]
        return result

    def _compile_clause(self, clause: TermQuery | BoolQuery) -> dict[str, Any]:
        if isinstance(clause, BoolQuery):
            return {"bool": self._compile_bool(clause)}
        return self._compile_term(clause)

    def _compile_term(self, term: TermQuery) -> dict[str, Any]:
        if term.mode == MatchMode.EXACT:
            return {"term": {term.field: {"value": term.value, "boost": term.boost}}}
        if term.mode == MatchMode.PREFIX:
            return {"prefix": {term.field: {"value": term.value, "boost": term.boost}}}
        if term.mode == MatchMode.PHRASE:
            return {"match_phrase": {term.field: {"query": term.value, "boost": term.boost}}}
        if term.mode == MatchMode.WILDCARD:
            return {"wildcard": {term.field: {"value": term.value, "boost": term.boost}}}
        return {
            "match": {
                term.field: {
                    "query": term.value,
                    "fuzziness": "AUTO",
                    "boost": term.boost,
                }
            }
        }

    def _build_filters(self, query: SearchQuery) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"organization_id": str(query.organization_id)}}]
        if query.resource_types:
            filters.append({"terms": {"resource_type": query.resource_types}})
        if query.folder_ids:
            filters.append({"terms": {"folder_id": [str(fid) for fid in query.folder_ids]}})
        if query.author_ids:
            filters.append({"terms": {"author_id": [str(aid) for aid in query.author_ids]}})
        if query.tags:
            filters.append({"terms": {"tags": query.tags}})
        if query.date_from or query.date_to:
            range_filter: dict[str, str] = {}
            if query.date_from:
                range_filter["gte"] = query.date_from.isoformat()
            if query.date_to:
                range_filter["lte"] = query.date_to.isoformat()
            filters.append({"range": {"updated_at": range_filter}})
        for field_filter in query.filters:
            filters.append(self._compile_filter(field_filter))
        return filters

    def _compile_filter(self, field_filter: FieldFilter) -> dict[str, Any]:
        if field_filter.operator == FilterOperator.EQ:
            return {"term": {field_filter.field_name: field_filter.value}}
        if field_filter.operator == FilterOperator.NE:
            return {"bool": {"must_not": [{"term": {field_filter.field_name: field_filter.value}}]}}
        if field_filter.operator == FilterOperator.IN:
            return {"terms": {field_filter.field_name: field_filter.values}}
        if field_filter.operator == FilterOperator.EXISTS:
            return {"exists": {"field": field_filter.field_name}}
        if field_filter.operator == FilterOperator.BETWEEN:
            return {
                "range": {
                    field_filter.field_name: {
                        "gte": field_filter.values[0],
                        "lte": field_filter.values[1],
                    }
                }
            }
        op_map = {
            FilterOperator.GT: "gt",
            FilterOperator.GTE: "gte",
            FilterOperator.LT: "lt",
            FilterOperator.LTE: "lte",
        }
        op = op_map.get(field_filter.operator)
        if op:
            return {"range": {field_filter.field_name: {op: field_filter.value}}}
        raise ValidationError(f"Unsupported filter operator: {field_filter.operator}")

    def _build_facet(self, facet: FacetRequest) -> dict[str, Any]:
        return {
            "field": facet.field,
            "size": facet.size,
            "min_count": facet.min_count,
        }

    def _build_sort(self, sort: SortOrder) -> list[dict[str, str]]:
        mapping = {
            SortOrder.RELEVANCE: [{"_score": "desc"}],
            SortOrder.UPDATED_DESC: [{"updated_at": "desc"}],
            SortOrder.UPDATED_ASC: [{"updated_at": "asc"}],
            SortOrder.TITLE_ASC: [{"title.keyword": "asc"}],
            SortOrder.TITLE_DESC: [{"title.keyword": "desc"}],
            SortOrder.CREATED_DESC: [{"created_at": "desc"}],
        }
        return mapping.get(sort, [{"_score": "desc"}])

    def _build_highlight(self, config: HighlightConfig) -> dict[str, Any]:
        return {
            "fields": {field: {} for field in config.fields},
            "fragment_size": config.fragment_size,
            "number_of_fragments": config.max_fragments,
            "pre_tags": [config.pre_tag],
            "post_tags": [config.post_tag],
        }

    def to_elasticsearch_body(self, built: BuiltQuery) -> dict[str, Any]:
        """Render BuiltQuery as an Elasticsearch request body."""
        body: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": built.must_clauses or [{"match_all": {}}],
                    "should": built.should_clauses,
                    "must_not": built.must_not_clauses,
                    "filter": built.filters,
                }
            },
            "sort": built.sort,
            "from": built.pagination["offset"],
            "size": built.pagination["limit"],
        }
        if built.facets:
            body["aggs"] = {
                f"facet_{facet['field']}": {
                    "terms": {"field": facet["field"], "size": facet["size"]}
                }
                for facet in built.facets
            }
        if built.highlight:
            body["highlight"] = built.highlight
        return body

    def explain_score(self, built: BuiltQuery) -> dict[str, Any]:
        """Return a human-readable explanation of query structure."""
        return {
            "organization_id": built.organization_id,
            "must_count": len(built.must_clauses),
            "should_count": len(built.should_clauses),
            "filter_count": len(built.filters),
            "facet_count": len(built.facets),
            "sort": built.sort,
            "pagination": built.pagination,
            "query_text": built.raw_query_text,
        }
