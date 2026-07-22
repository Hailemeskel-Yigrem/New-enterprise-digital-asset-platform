"""Unit tests for application mention parser."""

from __future__ import annotations

import uuid

from vaultforge.application.collaboration.mention_parser import (
    format_mention,
    parse_mentions,
    replace_mention_tokens,
)


def test_parse_mentions_extracts_display_and_ids() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    body = f"Hello {format_mention('Alice', user_a)} and {format_mention('Bob', user_b)}"
    result = parse_mentions(body)
    assert result.user_ids == [user_a, user_b]
    assert len(result.mentions) == 2
    assert result.mentions[0].display_name == "Alice"
    assert "@Alice" in result.plain_text


def test_parse_mentions_deduplicates() -> None:
    user_id = uuid.uuid4()
    token = format_mention("Repeat", user_id)
    result = parse_mentions(f"{token} again {token}")
    assert result.user_ids == [user_id]
    assert len(result.mentions) == 2


def test_format_mention_builds_canonical_token() -> None:
    user_id = uuid.uuid4()
    token = format_mention("Jane Doe", user_id)
    assert str(user_id) in token
    assert token.startswith("@[Jane Doe]")


def test_replace_mention_tokens_updates_names() -> None:
    user_id = uuid.uuid4()
    original = format_mention("Old Name", user_id)
    updated = replace_mention_tokens(original, {user_id: "New Name"})
    assert "New Name" in updated
    assert "Old Name" not in updated


def test_validate_mentions_flags_unknown() -> None:
    from vaultforge.application.collaboration.mention_parser import (
        validate_mentions,
    )

    known = uuid.uuid4()
    unknown = uuid.uuid4()
    body = f"{format_mention('Known', known)} {format_mention('Unknown', unknown)}"
    invalid = validate_mentions(body, {known})
    assert unknown in invalid
    assert known not in invalid


def test_strip_and_count_helpers() -> None:
    from vaultforge.application.collaboration.mention_parser import (
        count_mentions,
        mentions_to_notification_targets,
        strip_mention_tokens,
    )

    uid = uuid.uuid4()
    body = f"Ping {format_mention('User', uid)}"
    assert strip_mention_tokens(body) == "Ping @User"
    assert count_mentions(body) == 1
    assert mentions_to_notification_targets(body) == [uid]
