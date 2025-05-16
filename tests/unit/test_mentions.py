"""Unit tests for comment mention parsing."""

from __future__ import annotations

import uuid

from vaultforge.domain.collaboration.entities import Comment, extract_mention_user_ids


def test_extract_mention_user_ids_parses_tokens() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    body = f"Please review @[Alice]({user_a}) and @[Bob]({user_b})"

    ids = extract_mention_user_ids(body)
    assert ids == [user_a, user_b]


def test_extract_mention_user_ids_deduplicates() -> None:
    user_id = uuid.uuid4()
    body = f"Ping @[Alice]({user_id}) again @[Alice]({user_id})"

    ids = extract_mention_user_ids(body)
    assert ids == [user_id]


def test_comment_sync_mentions_creates_entities() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    comment = Comment(
        resource_type="document",
        resource_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        body=f"Hi @[A]({user_a}) and @[B]({user_b})",
    )

    mention_ids = extract_mention_user_ids(comment.body)
    mentions = comment.sync_mentions(mention_ids)

    assert len(mentions) == 2
    assert {mention.user_id for mention in mentions} == {user_a, user_b}
    assert all(mention.comment_id == comment.id for mention in mentions)


def test_extract_mention_user_ids_empty_body() -> None:
    assert extract_mention_user_ids("No mentions here") == []
