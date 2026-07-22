"""Application-layer mention parsing for comment bodies."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from vaultforge.domain.collaboration.entities import extract_mention_user_ids

MENTION_DISPLAY_PATTERN = re.compile(r"@\[([^\]]+)\]\(([0-9a-fA-F-]{36})\)")


@dataclass(frozen=True, slots=True)
class ParsedMention:
    user_id: uuid.UUID
    display_name: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class MentionParseResult:
    user_ids: list[uuid.UUID]
    mentions: tuple[ParsedMention, ...]
    plain_text: str


def parse_mentions(body: str) -> MentionParseResult:
    """Extract structured mentions and deduplicated user IDs from comment text."""
    mentions: list[ParsedMention] = []
    seen: set[uuid.UUID] = set()
    ordered_ids: list[uuid.UUID] = []

    for match in MENTION_DISPLAY_PATTERN.finditer(body):
        display_name = match.group(1).strip()
        user_id = uuid.UUID(match.group(2))
        mentions.append(
            ParsedMention(
                user_id=user_id,
                display_name=display_name,
                start=match.start(),
                end=match.end(),
            )
        )
        if user_id not in seen:
            seen.add(user_id)
            ordered_ids.append(user_id)

    # Fallback to domain helper for consistency
    domain_ids = extract_mention_user_ids(body)
    for uid in domain_ids:
        if uid not in seen:
            seen.add(uid)
            ordered_ids.append(uid)

    plain = MENTION_DISPLAY_PATTERN.sub(lambda m: f"@{m.group(1)}", body)
    return MentionParseResult(
        user_ids=ordered_ids,
        mentions=tuple(mentions),
        plain_text=plain,
    )


def format_mention(display_name: str, user_id: uuid.UUID) -> str:
    """Build a canonical mention token for rich-text editors."""
    safe_name = display_name.strip() or "User"
    return f"@[{safe_name}]({user_id})"


def replace_mention_tokens(body: str, mapping: dict[uuid.UUID, str]) -> str:
    """Replace mention UUIDs with updated display names."""

    def _replacer(match: re.Match[str]) -> str:
        uid = uuid.UUID(match.group(2))
        name = mapping.get(uid, match.group(1))
        return format_mention(name, uid)

    return MENTION_DISPLAY_PATTERN.sub(_replacer, body)


def validate_mentions(body: str, known_user_ids: set[uuid.UUID]) -> list[uuid.UUID]:
    """Return mention IDs that are not in the known set."""
    parsed = parse_mentions(body)
    return [uid for uid in parsed.user_ids if uid not in known_user_ids]


def strip_mention_tokens(body: str) -> str:
    """Remove mention markup leaving display names."""
    return MENTION_DISPLAY_PATTERN.sub(lambda m: f"@{m.group(1)}", body)


def count_mentions(body: str) -> int:
    return len(parse_mentions(body).mentions)


def mentions_to_notification_targets(body: str) -> list[uuid.UUID]:
    """IDs that should receive mention notifications."""
    return parse_mentions(body).user_ids
