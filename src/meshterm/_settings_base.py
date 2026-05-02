"""LayeredTomlSettings — meshterm's 4-layer Pydantic v2 settings base.

Provides a BaseSettings subclass with privacy-safe defaults and a clear
priority order for configuration sources. NO hardcoded paths to NFS,
hostnames, or usernames — every default resolves through the user's
environment so the package can be installed on any machine without
editing source.

Priority (highest → lowest):
    1. Explicit kwargs (init_settings)
    2. Environment vars  (MESHTERM_*  prefix; nested via __)
    3. Local TOML        (~/.config/meshterm/local.toml,  chmod 600)
    4. Workspace TOML    ($MESHTERM_WORKSPACE_CONFIG  or  ~/.config/meshterm/workspace.toml)
    5. Field defaults    (defined on the BaseSettings subclass)

Concrete settings classes subclass LayeredTomlSettings and declare their
own fields; this base only wires the source order.

Mirrors the claude-mesh sister-package settings shape but is duplicated
here intentionally to avoid a runtime cross-dependency on claude-mesh.

Privacy scrub note (v0.2.5): no shared-workspace paths, no usernames,
no hostnames are hardcoded in this module. The two TOML files are
user-local; the workspace one is always env-overridable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Type

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


def local_config_path() -> Path:
    """User's per-machine meshterm config (chmod 600 expected)."""
    return Path.home() / ".config" / "meshterm" / "local.toml"


def workspace_config_path() -> Path:
    """Workspace-shared config — env-driven, optional.

    If `MESHTERM_WORKSPACE_CONFIG` is set, use that path; otherwise fall
    back to `~/.config/meshterm/workspace.toml`. Never hardcoded to NFS.
    """
    env = os.environ.get("MESHTERM_WORKSPACE_CONFIG")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "meshterm" / "workspace.toml"


class LayeredTomlSettings(BaseSettings):
    """Pydantic v2 base wiring 4-layer config priority for meshterm.

    Subclasses declare their own fields; this base only wires the
    source order via `settings_customise_sources`.
    """

    model_config = SettingsConfigDict(
        env_prefix="MESHTERM_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls, local_config_path()),
            TomlConfigSettingsSource(settings_cls, workspace_config_path()),
        )


__all__ = [
    "LayeredTomlSettings",
    "local_config_path",
    "workspace_config_path",
]
