"""
AgentIA - Domain Pack Loader
Loads domain configuration (YAML) and renders prompt templates (Jinja2).
iRL-tech x EPINEXUS - Feb 2026
"""

import yaml
import os
import streamlit as st
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from jinja2 import Environment, FileSystemLoader

DOMAINS_DIR = Path(__file__).parent.parent / "domains"
DEFAULT_DOMAIN = "immobilier"


@dataclass
class DomainConfig:
    """Holds all domain-specific configuration."""
    id: str
    domain: dict
    app: dict
    segments: list
    pillars: list
    formats: dict
    market_data: dict
    ui: dict
    interview: dict
    demo_profiles: list
    prompts: dict = field(default_factory=dict)

    @property
    def app_name(self):
        return self.app.get("name", "AgentIA")

    @property
    def icon(self):
        return self.domain.get("icon", "\U0001f916")

    @property
    def professional_title(self):
        return self.domain.get("professional_title", "professionnel")

    @property
    def pillar_colors(self):
        colors = {p["key"]: p["color"] for p in self.pillars}
        colors["default"] = "#827568"
        return colors

    @property
    def pillar_labels(self):
        return {p["key"]: p["label"] for p in self.pillars}

    @property
    def pillar_keywords(self):
        return {p["key"]: p.get("keywords", []) for p in self.pillars}

    @property
    def platform_formats(self):
        return self.formats.get("platform_formats", {})

    @property
    def format_dimensions(self):
        """Return dict mapping (platform, format) tuples to dimension strings."""
        raw = self.formats.get("format_dimensions", {})
        result = {}
        for key, value in raw.items():
            parts = key.split("_", 1)
            if len(parts) == 2:
                result[(parts[0], parts[1])] = value
        return result

    @property
    def format_map(self):
        return self.formats.get("format_map", {})

    def get_prompt(self, name):
        """Get a rendered prompt by name (without extension)."""
        return self.prompts.get(name, "")

    def get_demo_dir(self):
        """Return path to this domain's demo directory."""
        return DOMAINS_DIR / self.id / "demo"


def _render_prompts(domain_dir, base_dir, config):
    """Render all Jinja2 prompt templates with domain config."""
    prompts = {}
    prompt_files = [
        "interview_conversation.md.j2",
        "persona_generation.md.j2",
        "benchmark_analysis.md.j2",
        "calendar_generation.md.j2",
        "content_generation.md.j2",
    ]

    for prompt_file in prompt_files:
        # Domain-specific prompt takes priority
        prompt_path = domain_dir / "prompts" / prompt_file
        if not prompt_path.exists() and base_dir.exists():
            # Fallback to _base
            prompt_path = base_dir / "prompts" / prompt_file

        if prompt_path.exists():
            key = prompt_file.replace(".md.j2", "")
            env = Environment(
                loader=FileSystemLoader(str(prompt_path.parent)),
                keep_trailing_newline=True,
            )
            template = env.get_template(prompt_path.name)
            prompts[key] = template.render(**config)

    return prompts


def load_domain(domain_id: Optional[str] = None) -> DomainConfig:
    """Load a domain pack from the domains directory.

    Resolution order for domain_id:
    1. Explicit parameter
    2. Environment variable AGENTIA_DOMAIN
    3. Default (immobilier)
    """
    domain_id = domain_id or os.environ.get("AGENTIA_DOMAIN", DEFAULT_DOMAIN)
    domain_dir = DOMAINS_DIR / domain_id
    base_dir = DOMAINS_DIR / "_base"

    if not domain_dir.exists():
        raise FileNotFoundError(f"Domain pack not found: {domain_dir}")

    config_path = domain_dir / "domain.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    prompts = _render_prompts(domain_dir, base_dir, config)

    return DomainConfig(
        id=domain_id,
        domain=config.get("domain", {}),
        app=config.get("app", {}),
        segments=config.get("segments", []),
        pillars=config.get("pillars", []),
        formats=config.get("formats", {}),
        market_data=config.get("market_data", {}),
        ui=config.get("ui", {}),
        interview=config.get("interview", {}),
        demo_profiles=config.get("demo_profiles", []),
        prompts=prompts,
    )


def get_domain() -> DomainConfig:
    """Get domain config, cached in session state."""
    if "domain_config" not in st.session_state:
        st.session_state.domain_config = load_domain()
    return st.session_state.domain_config
