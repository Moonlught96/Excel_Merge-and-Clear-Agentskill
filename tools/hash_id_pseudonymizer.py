from __future__ import annotations

import hashlib
import hmac
import json
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "hash-id.json"

EXCEL_ERROR_STRINGS = frozenset(
    {
        "#NULL!",
        "#DIV/0!",
        "#VALUE!",
        "#REF!",
        "#NAME?",
        "#NUM!",
        "#N/A",
        "#GETTING_DATA",
        "#SPILL!",
        "#CALC!",
        "#FIELD!",
        "#DATA!",
        "#BLOCKED!",
        "#UNKNOWN!",
        "#CONNECT!",
    }
)


class HashIdConfigError(ValueError):
    pass

class InvalidHashProjectContextError(ValueError):
    pass



class InvalidUserIdError(ValueError):
    pass


class UnknownPlatformError(ValueError):
    pass


@dataclass(frozen=True)
class HashProjectContext:
    project_id: str
    project_name: str
    key_version: int
    key_fingerprint: str
    secret_key: bytes = field(repr=False)


@dataclass(frozen=True)
class PlatformIdentityConfig:
    namespace: str
    aliases: tuple[str, ...]
    user_id_headers: tuple[str, ...]
    display_name_headers: tuple[str, ...]


@dataclass(frozen=True)
class HashIdConfig:
    schema_version: int
    algorithm_version: str
    platforms: tuple[PlatformIdentityConfig, ...]


@dataclass(frozen=True)
class SelectedIdentityHeader:
    source_header: str
    source_column: int
    identity_type: Literal["account_id", "display_name"]


def _require_string_list(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise HashIdConfigError(f"{field_name} must be a list of strings")
    return tuple(value)


def _require_identity_headers(value: Any, field_name: str) -> tuple[str, ...]:
    headers = _require_string_list(value, field_name)
    if any(not header.strip() for header in headers):
        raise HashIdConfigError(f"{field_name} must not contain blank headers")
    if len(set(headers)) != len(headers):
        raise HashIdConfigError(f"{field_name} must not contain duplicate headers")
    return headers


def load_hash_id_config(path: Path | str = DEFAULT_CONFIG_PATH) -> HashIdConfig:
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HashIdConfigError(f"Could not load hash ID config: {config_path}") from exc

    if not isinstance(raw, dict):
        raise HashIdConfigError("Hash ID config root must be an object")

    schema_version = raw.get("schema_version")
    algorithm_version = raw.get("algorithm_version")
    raw_platforms = raw.get("platforms")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        raise HashIdConfigError("schema_version must be 1")
    if algorithm_version != "bazhuayu-hash-id-v1":
        raise HashIdConfigError("algorithm_version must be bazhuayu-hash-id-v1")
    if not isinstance(raw_platforms, list):
        raise HashIdConfigError("platforms must be a list")

    platforms: list[PlatformIdentityConfig] = []
    registered_names: set[str] = set()
    for index, raw_platform in enumerate(raw_platforms):
        if not isinstance(raw_platform, dict):
            raise HashIdConfigError(f"platforms[{index}] must be an object")
        namespace = raw_platform.get("namespace")
        if not isinstance(namespace, str) or not namespace:
            raise HashIdConfigError(f"platforms[{index}].namespace must be a non-empty string")
        aliases = _require_string_list(raw_platform.get("aliases"), f"platforms[{index}].aliases")
        headers = _require_identity_headers(
            raw_platform.get("user_id_headers"),
            f"platforms[{index}].user_id_headers",
        )
        display_name_headers = _require_identity_headers(
            raw_platform.get("display_name_headers"),
            f"platforms[{index}].display_name_headers",
        )
        overlapping_headers = set(headers).intersection(display_name_headers)
        if overlapping_headers:
            raise HashIdConfigError(
                f"platforms[{index}] identity header lists must not overlap"
            )
        platform_names = set((namespace, *aliases))
        duplicate_names = registered_names.intersection(platform_names)
        if duplicate_names:
            duplicate_name = sorted(duplicate_names)[0]
            raise HashIdConfigError(f"Duplicate platform name in config: {duplicate_name}")
        registered_names.update(platform_names)
        platforms.append(
            PlatformIdentityConfig(
                namespace=namespace,
                aliases=aliases,
                user_id_headers=headers,
                display_name_headers=display_name_headers,
            )
        )

    return HashIdConfig(
        schema_version=schema_version,
        algorithm_version=algorithm_version,
        platforms=tuple(platforms),
    )


def normalize_platform(value: str, config: HashIdConfig) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnknownPlatformError("Platform is not registered")

    platform_name = value.strip()
    for platform in config.platforms:
        if platform_name == platform.namespace or platform_name in platform.aliases:
            return platform.namespace

    raise UnknownPlatformError(f"Platform is not registered: {platform_name!r}")


def normalize_raw_user_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise InvalidUserIdError("Invalid user ID value")
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.startswith("=") or normalized in EXCEL_ERROR_STRINGS:
            raise InvalidUserIdError("Invalid user ID value")
        return normalized
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise InvalidUserIdError("Invalid user ID value")
        return str(int(value))
    raise InvalidUserIdError("Invalid user ID value")


def _select_configured_identity_header(
    headers: list[Any],
    configured_headers: tuple[str, ...],
    identity_type: Literal["account_id", "display_name"],
) -> SelectedIdentityHeader | None:
    for configured_header in configured_headers:
        for source_column, header in enumerate(headers, start=1):
            if isinstance(header, str) and header == configured_header:
                return SelectedIdentityHeader(
                    source_header=header,
                    source_column=source_column,
                    identity_type=identity_type,
                )
    return None


def select_user_id_header(
    headers: list[Any],
    platform: str,
    config: HashIdConfig,
) -> SelectedIdentityHeader | None:
    namespace = normalize_platform(platform, config)
    platform_config = next(
        item for item in config.platforms if item.namespace == namespace
    )
    return _select_configured_identity_header(
        headers,
        platform_config.user_id_headers,
        "account_id",
    )


def select_identity_header(
    headers: list[Any],
    platform: str,
    config: HashIdConfig,
) -> SelectedIdentityHeader | None:
    namespace = normalize_platform(platform, config)
    platform_config = next(
        item for item in config.platforms if item.namespace == namespace
    )
    account_id_header = _select_configured_identity_header(
        headers,
        platform_config.user_id_headers,
        "account_id",
    )
    if account_id_header is not None:
        return account_id_header
    return _select_configured_identity_header(
        headers,
        platform_config.display_name_headers,
        "display_name",
    )


def _encode_length_prefixed(parts: tuple[str, ...]) -> bytes:
    encoded_parts: list[bytes] = []
    for part in parts:
        encoded = part.encode("utf-8")
        encoded_parts.append(struct.pack(">I", len(encoded)))
        encoded_parts.append(encoded)
    return b"".join(encoded_parts)


def _validate_project_context(context: HashProjectContext) -> None:
    if not isinstance(context.project_id, str) or not context.project_id.strip():
        raise InvalidHashProjectContextError("project_id must be a non-empty string")
    if not isinstance(context.secret_key, bytes) or len(context.secret_key) != 32:
        raise InvalidHashProjectContextError("secret_key must be exactly 32 bytes")
    if (
        not isinstance(context.key_version, int)
        or isinstance(context.key_version, bool)
        or context.key_version <= 0
    ):
        raise InvalidHashProjectContextError("key_version must be a positive integer")


def hash_user_id(
    value: Any,
    platform: str,
    context: HashProjectContext,
    config: HashIdConfig,
) -> str | None:
    _validate_project_context(context)
    namespace = normalize_platform(platform, config)
    normalized_user_id = normalize_raw_user_id(value)
    if normalized_user_id is None:
        return None

    message = _encode_length_prefixed(
        (
            config.algorithm_version,
            context.project_id,
            str(context.key_version),
            namespace,
            normalized_user_id,
        )
    )
    return hmac.new(context.secret_key, message, hashlib.sha256).hexdigest()
