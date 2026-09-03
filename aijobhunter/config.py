"""Central configuration: environment settings plus YAML config loaders.

Environment variables are injected via python-dotenv so a local ``.env`` file is
picked up automatically. Three YAML files carry the non-secret config: the
portals to scan, the candidate profile, and the include/exclude keywords used by
the filter stage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env once, at import time, so every module sees the same environment.
load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


@dataclass
class Settings:
    """Runtime settings resolved from environment variables."""

    # LLM (local Ollama)
    ollama_base_url: str = field(
        default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3"))
    llm_temperature: float = field(
        default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.2"))
    )

    # Storage / output
    db_path: str = field(default_factory=lambda: _env("AIJOBHUNTER_DB_PATH", "./data/aijobhunter.db"))
    output_dir: str = field(default_factory=lambda: _env("AIJOBHUNTER_OUTPUT_DIR", "./output"))

    # Config files
    portals_config: str = field(
        default_factory=lambda: _env("AIJOBHUNTER_PORTALS_CONFIG", "./config/portals.yaml")
    )
    profile_config: str = field(
        default_factory=lambda: _env("AIJOBHUNTER_PROFILE_CONFIG", "./config/profile.yaml")
    )
    keywords_config: str = field(
        default_factory=lambda: _env("AIJOBHUNTER_KEYWORDS_CONFIG", "./config/keywords.yaml")
    )

    # Relevance / browser
    score_threshold: int = field(
        default_factory=lambda: int(_env("AIJOBHUNTER_SCORE_THRESHOLD", "70"))
    )
    # Max jobs a single batch action (assess-fit / draft) processes in the TUI.
    batch_size: int = field(default_factory=lambda: int(_env("AIJOBHUNTER_BATCH_SIZE", "5")))
    browser_profile_dir: str = field(
        default_factory=lambda: _env(
            "AIJOBHUNTER_BROWSER_PROFILE_DIR", "./data/browser-profile"
        )
    )


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file into a dict, raising a clear error if it is missing."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Config file not found: {p}. Copy the matching *.example.yaml and edit it."
        )
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping at the top of {p}, got {type(data).__name__}")
    return data


def load_portals(settings: Settings) -> list[dict[str, Any]]:
    """Return the enabled portal entries from the portals YAML."""
    data = load_yaml(settings.portals_config)
    portals = data.get("portals", [])
    return [p for p in portals if p.get("enabled", True)]


def load_profile(settings: Settings) -> dict[str, Any]:
    """Return the candidate profile, resolving ``resume_file`` if provided.

    ``resume_file`` may be a .txt/.md/.pdf/.docx path; its extracted text
    replaces ``resume_text``.
    """
    data = load_yaml(settings.profile_config)
    resume_file = data.get("resume_file")
    if resume_file:
        from .documents import read_document

        data["resume_text"] = read_document(resume_file)
    return data


def load_keywords(settings: Settings) -> dict[str, list[str]]:
    """Return ``{"include": [...], "exclude": [...]}`` from the keywords YAML."""
    data = load_yaml(settings.keywords_config)
    return {
        "include": [str(k).strip() for k in data.get("include", []) if str(k).strip()],
        "exclude": [str(k).strip() for k in data.get("exclude", []) if str(k).strip()],
    }


def save_keywords(settings: Settings, include: list[str], exclude: list[str]) -> str:
    """Write include/exclude keywords to the keywords YAML. Returns the path."""
    path = Path(settings.keywords_config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump({"include": include, "exclude": exclude}, fh, sort_keys=False)
    return str(path)
