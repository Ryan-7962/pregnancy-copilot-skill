from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .storage import PregnancyDataStore, SCHEMA_VERSION, atomic_write_text, safe_path_component


REGISTRY_FILE = "identity_bindings.yaml"
LOCAL_BINDING_PATH = "memory/identity_binding.yaml"


class IdentityBindingError(PermissionError):
    pass


@dataclass(frozen=True)
class IdentityEndpoint:
    channel: str
    conversation_id: str
    sender_id: str

    def normalized(self) -> dict[str, str]:
        return {
            "channel": safe_path_component(self.channel, "channel"),
            "conversation_id": self.conversation_id.strip(),
            "sender_id": self.sender_id.strip(),
        }


class IdentityRegistry:
    def __init__(self, base_root: str | Path):
        self.base_root = Path(base_root)
        self.store = PregnancyDataStore(self.base_root)
        self.path = self.base_root / REGISTRY_FILE

    def resolve_or_create(self, pregnancy_id: str, endpoint: IdentityEndpoint) -> Path:
        identity = safe_identity_id(pregnancy_id)
        endpoint_data = endpoint.normalized()
        with self.store.transaction_lock("identity-registry"):
            registry = self._load()
            bound_identity = find_bound_identity(registry, endpoint_data)
            if bound_identity and bound_identity != identity:
                raise IdentityBindingError(f"Endpoint is already bound to pregnancy identity {bound_identity!r}.")
            existing = registry["identities"].get(identity)
            if existing:
                if endpoint_data not in existing.get("endpoints", []):
                    raise IdentityBindingError(
                        f"Endpoint is not bound to existing pregnancy identity {identity!r}; explicit authorization is required."
                    )
            else:
                registry["identities"][identity] = {
                    "data_root": f"identities/{identity}",
                    "endpoints": [endpoint_data],
                }
                self._write(registry)
        return self.data_root_for(identity)

    def bind_endpoint(self, pregnancy_id: str, endpoint: IdentityEndpoint) -> Path:
        identity = safe_identity_id(pregnancy_id)
        endpoint_data = endpoint.normalized()
        with self.store.transaction_lock("identity-registry"):
            registry = self._load()
            existing = registry["identities"].get(identity)
            if not existing:
                raise IdentityBindingError(f"Pregnancy identity {identity!r} does not exist.")
            bound_identity = find_bound_identity(registry, endpoint_data)
            if bound_identity and bound_identity != identity:
                raise IdentityBindingError(f"Endpoint is already bound to pregnancy identity {bound_identity!r}.")
            if endpoint_data not in existing.get("endpoints", []):
                existing.setdefault("endpoints", []).append(endpoint_data)
                self._write(registry)
        data_root = self.data_root_for(identity)
        if (data_root / LOCAL_BINDING_PATH).exists():
            authorize_local_endpoint(data_root, endpoint)
        return data_root

    def data_root_for(self, pregnancy_id: str) -> Path:
        identity = safe_identity_id(pregnancy_id)
        return self.base_root / "identities" / identity

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": SCHEMA_VERSION, "identities": {}}
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise IdentityBindingError("Unsupported identity registry schema version.")
        payload.setdefault("identities", {})
        return payload

    def _write(self, registry: dict[str, Any]) -> None:
        atomic_write_text(self.path, yaml.safe_dump(registry, allow_unicode=True, sort_keys=False))


def ensure_local_identity_binding(data_root: str | Path, endpoint: IdentityEndpoint) -> None:
    root = Path(data_root)
    store = PregnancyDataStore(root)
    path = root / LOCAL_BINDING_PATH
    endpoint_data = endpoint.normalized()
    with store.transaction_lock("local-identity"):
        if path.exists():
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            endpoints = payload.get("endpoints") or []
            if endpoint_data not in endpoints:
                raise IdentityBindingError(
                    "Endpoint is not bound to this pregnancy data root; use a separate pregnancy_id or explicitly authorize it."
                )
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "identity_mode": "single_pregnancy_root",
            "endpoints": [endpoint_data],
        }
        atomic_write_text(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def authorize_local_endpoint(data_root: str | Path, endpoint: IdentityEndpoint) -> None:
    root = Path(data_root)
    store = PregnancyDataStore(root)
    path = root / LOCAL_BINDING_PATH
    endpoint_data = endpoint.normalized()
    with store.transaction_lock("local-identity"):
        if not path.exists():
            raise IdentityBindingError("Local pregnancy identity has not been initialized.")
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        endpoints = payload.setdefault("endpoints", [])
        if endpoint_data not in endpoints:
            endpoints.append(endpoint_data)
            atomic_write_text(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def find_bound_identity(registry: dict[str, Any], endpoint: dict[str, str]) -> str | None:
    for identity, record in registry.get("identities", {}).items():
        if endpoint in record.get("endpoints", []):
            return str(identity)
    return None


def safe_identity_id(value: str) -> str:
    safe = safe_path_component(value, "pregnancy_id")
    if safe != value.strip():
        raise ValueError(f"Unsafe pregnancy_id: {value!r}")
    return safe
