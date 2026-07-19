"""Custom metadata schema and value domain entities."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import Entity

_FIELD_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_MAX_SCHEMA_FIELDS = 128
_MAX_STRING_LENGTH = 8192
_MAX_MULTI_SELECT = 64


class MetadataFieldType:
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"
    MULTI_ENUM = "multi_enum"
    JSON = "json"
    URL = "url"
    EMAIL = "email"

    ALL = frozenset(
        {
            STRING,
            TEXT,
            INTEGER,
            DECIMAL,
            BOOLEAN,
            DATE,
            DATETIME,
            ENUM,
            MULTI_ENUM,
            JSON,
            URL,
            EMAIL,
        }
    )


@dataclass(frozen=True, slots=True)
class MetadataFieldDefinition:
    key: str
    label: str
    field_type: str
    required: bool = False
    description: str = ""
    default_value: Any = None
    enum_options: tuple[str, ...] = ()
    min_value: int | Decimal | None = None
    max_value: int | Decimal | None = None
    min_length: int | None = None
    max_length: int | None = None
    searchable: bool = True
    sort_order: int = 0

    def __post_init__(self) -> None:
        if not _FIELD_KEY_PATTERN.match(self.key):
            raise ValidationError(f"Invalid metadata field key: {self.key}")
        if self.field_type not in MetadataFieldType.ALL:
            raise ValidationError(f"Unsupported field type: {self.field_type}")
        if (
            self.field_type in (MetadataFieldType.ENUM, MetadataFieldType.MULTI_ENUM)
            and not self.enum_options
        ):
            raise ValidationError(f"Enum field {self.key} requires enum_options")

    def validate_value(self, value: Any) -> Any:
        if value is None:
            if self.required:
                raise ValidationError(f"Field {self.key} is required")
            return None
        return _coerce_and_validate(self, value)


def _coerce_and_validate(defn: MetadataFieldDefinition, value: Any) -> Any:
    ft = defn.field_type
    if ft == MetadataFieldType.STRING:
        if not isinstance(value, str):
            raise ValidationError(f"{defn.key} must be a string")
        cleaned = value.strip()
        _check_length(defn, cleaned)
        return cleaned
    if ft == MetadataFieldType.TEXT:
        if not isinstance(value, str):
            raise ValidationError(f"{defn.key} must be text")
        _check_length(defn, value)
        return value
    if ft == MetadataFieldType.INTEGER:
        try:
            coerced = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{defn.key} must be an integer") from exc
        _check_bounds(defn, coerced)
        return coerced
    if ft == MetadataFieldType.DECIMAL:
        try:
            decimal_value = Decimal(str(value))
        except Exception as exc:
            raise ValidationError(f"{defn.key} must be a decimal") from exc
        _check_bounds(defn, decimal_value)
        return decimal_value
    if ft == MetadataFieldType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
        raise ValidationError(f"{defn.key} must be a boolean")
    if ft == MetadataFieldType.ENUM:
        if not isinstance(value, str) or value not in defn.enum_options:
            raise ValidationError(f"{defn.key} value not in allowed options")
        return value
    if ft == MetadataFieldType.MULTI_ENUM:
        if not isinstance(value, list):
            raise ValidationError(f"{defn.key} must be a list")
        allowed = set(defn.enum_options)
        return [v for v in value if isinstance(v, str) and v in allowed]
    if ft == MetadataFieldType.JSON:
        if isinstance(value, dict | list):
            return value
        if isinstance(value, str):
            return json.loads(value)
        raise ValidationError(f"{defn.key} must be JSON")
    if ft == MetadataFieldType.URL:
        if not isinstance(value, str) or not value.startswith(("http://", "https://")):
            raise ValidationError(f"{defn.key} must be http(s) URL")
        return value
    if ft == MetadataFieldType.EMAIL:
        if not isinstance(value, str) or "@" not in value:
            raise ValidationError(f"{defn.key} must be valid email")
        return value.lower().strip()
    raise ValidationError(f"Unhandled field type for {defn.key}")


def _check_length(defn: MetadataFieldDefinition, value: str) -> None:
    max_len = defn.max_length or _MAX_STRING_LENGTH
    if len(value) > max_len:
        raise ValidationError(f"{defn.key} exceeds max length")


def _check_bounds(defn: MetadataFieldDefinition, value: int | Decimal) -> None:
    if defn.min_value is not None and value < defn.min_value:
        raise ValidationError(f"{defn.key} below minimum")
    if defn.max_value is not None and value > defn.max_value:
        raise ValidationError(f"{defn.key} above maximum")


@dataclass(slots=True)
class MetadataSchema(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    slug: str = ""
    description: str = ""
    resource_type: str = "document"
    version: int = 1
    is_active: bool = True
    fields: list[MetadataFieldDefinition] = field(default_factory=list)
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.slug.strip():
            raise ValidationError("Schema name and slug are required")
        if len({f.key for f in self.fields}) != len(self.fields):
            raise ValidationError("Duplicate field keys in schema")

    def field_map(self) -> dict[str, MetadataFieldDefinition]:
        return {f.key: f for f in self.fields}

    def validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        field_map = self.field_map()
        unknown = set(payload.keys()) - set(field_map.keys())
        if unknown:
            raise ValidationError(f"Unknown metadata fields: {sorted(unknown)}")
        return {k: field_map[k].validate_value(payload.get(k)) for k in field_map}

    def apply_defaults(self, payload: dict[str, Any]) -> dict[str, Any]:
        merged = dict(payload)
        for defn in self.fields:
            if defn.key not in merged and defn.default_value is not None:
                merged[defn.key] = defn.default_value
        return merged

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def bump_version(self) -> None:
        self.version += 1
        self.touch()


@dataclass(slots=True)
class MetadataValue(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    schema_id: uuid.UUID = field(default_factory=uuid.uuid4)
    schema_version: int = 1
    resource_type: str = "document"
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    values: dict[str, Any] = field(default_factory=dict)
    updated_by: uuid.UUID = field(default_factory=uuid.uuid4)

    def merge(self, patch: dict[str, Any], schema: MetadataSchema) -> dict[str, Any]:
        validated = schema.validate_payload({**self.values, **patch})
        self.values = validated
        self.schema_version = schema.version
        self.touch()
        return validated

    def replace(self, payload: dict[str, Any], schema: MetadataSchema) -> dict[str, Any]:
        validated = schema.validate_payload(schema.apply_defaults(payload))
        self.values = validated
        self.schema_version = schema.version
        self.touch()
        return validated


@dataclass(frozen=True, slots=True)
class MetadataQueryFilter:
    organization_id: uuid.UUID
    schema_id: uuid.UUID | None = None
    resource_type: str | None = None
    resource_ids: frozenset[uuid.UUID] = frozenset()
    field_key: str | None = None
    field_value: str | None = None
    limit: int = 100
    offset: int = 0
