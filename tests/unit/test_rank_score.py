"""Tests for global search ranking heuristic."""

from vaultforge.application.analytics.global_search_service import rank_score


def test_name_hit_outranks_tag_only() -> None:
    assert rank_score(name_hit=True, tag_hit=False, recency_days=0) > rank_score(
        name_hit=False, tag_hit=True, recency_days=0
    )


def test_recent_docs_score_higher() -> None:
    assert rank_score(name_hit=True, tag_hit=False, recency_days=1) > rank_score(
        name_hit=True, tag_hit=False, recency_days=90
    )
