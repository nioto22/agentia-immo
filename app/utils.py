"""
AgentIA - Shared Utilities
Common functions used across all modules.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import anthropic
import json
import re
import os
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
# Static defaults (overridden by domain config at runtime)
APP_TITLE = "AgentIA"
APP_ICON = "\U0001f3e0"
MODEL_CONVERSATION = "claude-haiku-4-5-20251001"   # Fast & cheap for Q&A / structured data
MODEL_PERSONA = "claude-sonnet-4-5-20250929"        # Quality for complex generation (Sonnet 4.5)

# --- PRICING per million tokens ---
MODEL_PRICING = {
    MODEL_CONVERSATION: {"input": 1.0, "output": 5.0, "cache_read": 0.10, "cache_write": 1.25},
    MODEL_PERSONA: {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
}

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DATA_DIR = Path(__file__).parent.parent / "data"

# --- DOMAIN CONFIG (lazy loaded) ---
def _get_domain():
    """Get domain config lazily (avoids circular imports)."""
    from domain_loader import get_domain
    return get_domain()


def get_app_title():
    """Get app title from domain config."""
    try:
        return _get_domain().app_name
    except Exception:
        return APP_TITLE


def get_app_icon():
    """Get app icon from domain config."""
    try:
        return _get_domain().icon
    except Exception:
        return APP_ICON

# --- CUSTOM CSS (copper theme) ---
AGENTIA_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

    .stApp { background-color: #FAFAF8; }

    .agent-header {
        background: linear-gradient(135deg, #F5F0E6 0%, #ede4d6 60%, rgba(184,115,51,0.12) 100%);
        border-bottom: 3px solid #B87333;
        padding: 1.5rem 2rem;
        border-radius: 12px 12px 0 0;
        margin-bottom: 0;
    }
    .agent-header h1 {
        font-family: 'Space Grotesk', sans-serif;
        color: #171412; font-size: 1.8rem; font-weight: 700; margin: 0; letter-spacing: -0.02em;
    }
    .agent-header p { color: #827568; font-size: 0.95rem; margin: 0.25rem 0 0 0; }
    .agent-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(184,115,51,0.15); color: #9A5F2A;
        padding: 3px 12px; border-radius: 100px;
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.08em; margin-bottom: 0.5rem;
    }

    .persona-output {
        background: #FFFFFF; border: 2px solid #B87333; border-radius: 12px;
        padding: 2rem; margin: 1rem 0; box-shadow: 0 4px 12px rgba(184,115,51,0.08);
    }

    .sidebar-info {
        background: #F5F0E6; border-radius: 8px; padding: 1rem;
        margin-bottom: 1rem; border-left: 3px solid #B87333;
    }
    .sidebar-info h4 { color: #B87333; margin: 0 0 0.5rem 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .sidebar-info p { color: #524b46; font-size: 0.85rem; margin: 0.25rem 0; }

    .cost-badge {
        background: #f0f0ee; border-radius: 6px; padding: 4px 10px;
        font-size: 0.7rem; color: #827568; display: inline-block; margin-top: 0.5rem;
    }

    .content-card {
        background: #FFFFFF; border: 1px solid #e8e0d6; border-radius: 12px;
        padding: 1.5rem; margin: 1rem 0; box-shadow: 0 2px 8px rgba(184,115,51,0.06);
    }
    .content-card-header {
        background: linear-gradient(135deg, #F5F0E6, #ede4d6);
        border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem;
        border-left: 3px solid #B87333;
    }
    .content-card-header h4 {
        color: #9A5F2A; margin: 0; font-size: 0.9rem; font-weight: 600;
    }

    .platform-badge {
        display: inline-block; padding: 2px 10px; border-radius: 100px;
        font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; margin-right: 0.5rem;
    }
    .platform-instagram { background: #fce4ec; color: #c2185b; }
    .platform-linkedin { background: #e3f2fd; color: #1565c0; }
    .platform-facebook { background: #e8eaf6; color: #283593; }

    .calendar-day {
        background: #FFFFFF; border: 1px solid #e8e0d6; border-radius: 8px;
        padding: 0.75rem; margin: 0.25rem 0;
    }
    .calendar-day-rest {
        background: #fafafa; border: 1px dashed #ddd; border-radius: 8px;
        padding: 0.75rem; margin: 0.25rem 0; opacity: 0.6;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
</style>
"""

# --- CALENDAR CARD CSS (shared between Calendrier and Contenu) ---
CALENDAR_CARD_CSS = """
<style>
    /* --- Modern card (Option E) --- */
    .mc {
        background: #FFFFFF; border-radius: 12px; overflow: hidden;
        border: 1px solid #e8e0d6; margin-bottom: 0.25rem;
    }
    .mc-rest {
        background: #FFFFFF; border-radius: 12px; overflow: hidden;
        border: 1px dashed #ddd; margin-bottom: 0.25rem; opacity: 0.5;
    }

    /* Top row: big number + weekday + platform */
    .mc-top {
        padding: 0.65rem 0.85rem 0.4rem; display: flex; align-items: center; gap: 0.65rem;
    }
    .mc-num {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem; font-weight: 700; color: #B87333; line-height: 1; min-width: 36px;
    }
    .mc-num-rest { color: #ccc; }
    .mc-weekday {
        font-size: 0.7rem; color: #827568; text-transform: uppercase;
        font-weight: 600; letter-spacing: 0.05em;
    }
    .mc-badges { display: flex; gap: 0.35rem; flex-wrap: wrap; align-items: center; }

    /* Platform badge */
    .mc-plat {
        display: inline-block; padding: 2px 8px; border-radius: 100px;
        font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .mc-plat-instagram { background: #fce4ec; color: #c2185b; }
    .mc-plat-linkedin { background: #e3f2fd; color: #1565c0; }
    .mc-plat-facebook { background: #e8eaf6; color: #283593; }

    /* Format badge */
    .mc-fmt {
        display: inline-block; padding: 2px 8px; border-radius: 100px;
        font-size: 0.65rem; font-weight: 600; background: #F5F0E6; color: #9A5F2A;
    }

    /* Body: short description */
    .mc-body {
        padding: 0 0.85rem 0.5rem; font-size: 0.78rem; color: #444; line-height: 1.4;
        border-top: 1px solid #f0ece6;
    }

    /* Footer: time + pillar */
    .mc-foot {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.35rem 0.85rem; background: #fafaf8; font-size: 0.65rem; color: #827568;
    }
    .mc-pillar {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.6rem; font-weight: 600; color: #fff;
    }

    /* Popover detail card */
    .pop-num {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.5rem; font-weight: 700; color: #B87333; line-height: 1;
    }
    .pop-pillar {
        display: inline-block; padding: 3px 12px; border-radius: 6px;
        font-size: 0.75rem; font-weight: 600; color: #fff;
    }

    /* Stories section */
    .stories-box {
        background: #F5F0E6; border-radius: 8px; padding: 0.75rem 1rem;
        margin-top: 0.75rem; border-left: 3px solid #B87333;
        font-size: 0.78rem; color: #524b46;
    }

    /* Legend */
    .legend-row {
        display: flex; gap: 0.75rem; flex-wrap: wrap;
        font-size: 0.7rem; color: #827568; margin-bottom: 0.75rem;
    }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .legend-dot { width: 10px; height: 10px; border-radius: 3px; }

    /* Week title */
    .week-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.05rem; font-weight: 700; color: #171412;
        padding-bottom: 0.4rem; border-bottom: 2px solid #B87333;
        margin: 1.5rem 0 0.75rem;
    }
    .week-title:first-child { margin-top: 0; }
</style>
"""


# --- PILLAR COLORS / LABELS / FORMAT DIMENSIONS ---
# These are now loaded from domain config with hardcoded fallbacks.

_FALLBACK_PILLAR_COLORS = {
    "property": "#E65100",
    "market": "#1565C0",
    "behind": "#6A1B9A",
    "lifestyle": "#2E7D32",
    "success": "#F9A825",
    "default": "#827568",
}

_FALLBACK_PILLAR_LABELS = {
    "property": "Biens & Proprietes",
    "market": "Expertise Marche",
    "behind": "Coulisses",
    "lifestyle": "Lifestyle",
    "success": "Succes Clients",
}

_FALLBACK_FORMAT_DIMENSIONS = {
    ("Instagram", "Post standard"): "1080 x 1440 px (3:4)",
    ("Instagram", "Carrousel"): "1080 x 1440 px x N slides",
    ("Instagram", "Reel"): "1080 x 1920 px (9:16)",
    ("Instagram", "Story"): "1080 x 1920 px (9:16)",
    ("LinkedIn", "Post standard"): "1200 x 628 px (1.91:1)",
    ("LinkedIn", "Carrousel"): "1080 x 1080 px (PDF)",
    ("LinkedIn", "Article"): "1200 x 628 px (cover)",
    ("Facebook", "Post standard"): "1200 x 630 px (1.91:1)",
    ("Facebook", "Reel"): "1080 x 1920 px (9:16)",
    ("Facebook", "Story"): "1080 x 1920 px (9:16)",
}


def get_pillar_colors():
    try:
        return _get_domain().pillar_colors
    except Exception:
        return _FALLBACK_PILLAR_COLORS


def get_pillar_labels():
    try:
        return _get_domain().pillar_labels
    except Exception:
        return _FALLBACK_PILLAR_LABELS


def get_format_dimensions():
    try:
        return _get_domain().format_dimensions
    except Exception:
        return _FALLBACK_FORMAT_DIMENSIONS


# Backwards-compatible module-level aliases (read at import time, won't update dynamically)
# Pages should prefer the get_* functions for dynamic loading.
PILLAR_COLORS = _FALLBACK_PILLAR_COLORS
PILLAR_LABELS = _FALLBACK_PILLAR_LABELS
FORMAT_DIMENSIONS = _FALLBACK_FORMAT_DIMENSIONS


def inject_css():
    """Inject the shared AgentIA CSS theme."""
    st.markdown(AGENTIA_CSS, unsafe_allow_html=True)


def inject_calendar_css():
    """Inject the calendar card CSS (for Calendrier and Contenu modules)."""
    st.markdown(CALENDAR_CARD_CSS, unsafe_allow_html=True)


def load_prompt(filename):
    """Load a rendered prompt from domain config, with file fallback."""
    # Try domain config first (rendered Jinja2 templates)
    try:
        domain = _get_domain()
        key = filename.replace(".md", "").replace(".j2", "")
        prompt = domain.get_prompt(key)
        if prompt:
            return prompt
    except Exception:
        pass

    # Fallback to raw file
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_client():
    """Get Anthropic client from st.secrets or environment variable."""
    api_key = None

    # Priority 1: st.secrets
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass

    # Priority 2: environment variable
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def check_api_key():
    """Check if API key is configured. Stops the page if not."""
    client = get_client()
    if not client:
        st.error(
            "Cle API non configuree. Contactez l'administrateur AgentIA "
            "ou configurez `ANTHROPIC_API_KEY` dans `.streamlit/secrets.toml` ou en variable d'environnement.",
            icon="\U0001f512",
        )
        st.stop()


def _track_usage(usage, model):
    """Track token usage and cost from API response."""
    model = model or MODEL_CONVERSATION
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[MODEL_CONVERSATION])

    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0

    st.session_state.setdefault("total_input_tokens", 0)
    st.session_state.setdefault("total_output_tokens", 0)
    st.session_state.setdefault("total_cache_read_tokens", 0)
    st.session_state.setdefault("total_cache_write_tokens", 0)
    st.session_state.setdefault("total_cost", 0.0)

    st.session_state["total_input_tokens"] += input_tokens
    st.session_state["total_output_tokens"] += output_tokens
    st.session_state["total_cache_read_tokens"] += cache_read
    st.session_state["total_cache_write_tokens"] += cache_write

    # Non-cached input = total input - cache_read - cache_write
    standard_input = max(0, input_tokens - cache_read - cache_write)
    cost = (
        standard_input * pricing["input"] / 1_000_000
        + cache_read * pricing["cache_read"] / 1_000_000
        + cache_write * pricing["cache_write"] / 1_000_000
        + output_tokens * pricing["output"] / 1_000_000
    )
    st.session_state["total_cost"] += cost


def _build_system_param(system_prompt):
    """Build system parameter with prompt caching enabled."""
    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _handle_api_error(e):
    """Map Anthropic exceptions to user-friendly error messages."""
    if isinstance(e, anthropic.BadRequestError):
        if "credit balance" in str(e):
            return "Credits API insuffisants. Rechargez sur console.anthropic.com > Plans & Billing."
        return f"Erreur API : {e}"
    if isinstance(e, anthropic.AuthenticationError):
        return "Cle API invalide. Contactez l'administrateur AgentIA."
    if isinstance(e, anthropic.RateLimitError):
        return "Limite de requetes atteinte. Reessayez dans quelques secondes."
    if isinstance(e, anthropic.APIError):
        return f"Erreur API Anthropic : {e}"
    return f"Erreur inattendue : {e}"


def chat_with_claude(messages, system_prompt, model=None, max_tokens=None):
    """Send messages to Claude and get a response. Returns (text, error).

    Prompt caching is enabled automatically on the system prompt.
    """
    client = get_client()
    if not client:
        return None, "Cle API non configuree. Contactez l'administrateur AgentIA."

    model = model or MODEL_CONVERSATION
    max_tokens = max_tokens or 1024
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_build_system_param(system_prompt),
            messages=api_messages,
        )
        _track_usage(response.usage, model)
        return response.content[0].text, None
    except (anthropic.BadRequestError, anthropic.AuthenticationError,
            anthropic.RateLimitError, anthropic.APIError) as e:
        return None, _handle_api_error(e)


def chat_with_claude_stream(messages, system_prompt, model=None, max_tokens=None):
    """Stream a response from Claude. Yields text chunks.

    Returns a generator of text chunks. Call list() or iterate to consume.
    After iteration, check st.session_state for usage tracking.
    Usage is tracked when the stream completes.
    """
    client = get_client()
    if not client:
        yield "[ERREUR] Cle API non configuree."
        return

    model = model or MODEL_CONVERSATION
    max_tokens = max_tokens or 1024
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=_build_system_param(system_prompt),
            messages=api_messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
            # Track usage after stream completes
            response = stream.get_final_message()
            _track_usage(response.usage, model)
    except (anthropic.BadRequestError, anthropic.AuthenticationError,
            anthropic.RateLimitError, anthropic.APIError) as e:
        yield f"[ERREUR] {_handle_api_error(e)}"


def estimate_cost():
    """Return tracked API cost and token counts."""
    input_tokens = st.session_state.get("total_input_tokens", 0)
    output_tokens = st.session_state.get("total_output_tokens", 0)
    cost = st.session_state.get("total_cost", 0.0)
    return cost, input_tokens, output_tokens


def render_sidebar(module_name="", module_help=""):
    """Render the shared sidebar with navigation and cost tracking."""
    with st.sidebar:
        st.markdown("### AgentIA")

        # Navigation
        st.page_link("main.py", label="Tableau de Bord", icon="\U0001f4ca")
        st.page_link("pages/1_\U0001f3af_Profil.py", label="1. Profil & Persona", icon="\U0001f3af")
        st.page_link("pages/2_\U0001f50d_Veille.py", label="2. Veille & Benchmark", icon="\U0001f50d")
        st.page_link("pages/3_\U0001f4c5_Calendrier.py", label="3. Calendrier Editorial", icon="\U0001f4c5")
        st.page_link("pages/4_\u270f\ufe0f_Contenu.py", label="4. Creation de Contenu", icon="\u270f\ufe0f")

        st.divider()

        if module_help:
            st.markdown(f'<div class="sidebar-info"><h4>{module_name}</h4>{module_help}</div>', unsafe_allow_html=True)

        # Cost display
        cost, in_tok, out_tok = estimate_cost()
        if in_tok > 0:
            st.caption(f"Tokens: {in_tok:,} in / {out_tok:,} out")
            st.caption(f"Cout estime: ~${cost:.3f}")

        st.divider()
        st.caption("iRL-tech x EPINEXUS | v0.3")


# --- SHARED CALENDAR FUNCTIONS (used by Calendrier + Contenu) ---

def classify_pillar(pillar_text):
    """Map a pillar name from the AI output to a color key using domain config."""
    if not pillar_text:
        return "default"
    p = pillar_text.lower()
    try:
        keywords = _get_domain().pillar_keywords
        for key, words in keywords.items():
            if any(w in p for w in words):
                return key
    except Exception:
        pass
    # Hardcoded fallback
    if any(w in p for w in ["property", "propr", "bien", "listing"]):
        return "property"
    if any(w in p for w in ["market", "march", "insight", "expert"]):
        return "market"
    if any(w in p for w in ["behind", "couliss", "scenes", "personal"]):
        return "behind"
    if any(w in p for w in ["lifestyle", "life", "commun", "local"]):
        return "lifestyle"
    if any(w in p for w in ["success", "succes", "client", "temoign"]):
        return "success"
    return "default"


def parse_calendar_json(content):
    """Extract and parse JSON data from calendar content (robust)."""
    # Strategy 1: exact HTML comment markers
    match = re.search(r'<!--\s*CALENDAR_JSON\s*(.*?)\s*CALENDAR_JSON\s*-->', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 2: markers without proper HTML comment syntax
    match = re.search(r'CALENDAR_JSON\s*(\{.*?\})\s*CALENDAR_JSON', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: find any JSON block containing "weeks" key (code fence or raw)
    for pattern in [
        r'```json\s*(\{.*?"weeks".*?\})\s*```',
        r'```\s*(\{.*?"weeks".*?\})\s*```',
        r'(\{[^{}]*"weeks"\s*:\s*\[.*\]\s*\})',
    ]:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                continue

    return None


def get_markdown_content(content):
    """Return the markdown portion (without the hidden JSON block)."""
    return re.sub(r'<!--CALENDAR_JSON.*?CALENDAR_JSON-->', '', content, flags=re.DOTALL).strip()


# --- PERSONA / BENCHMARK / CALENDAR LOADING ---

def load_persona_from_session():
    """Try to load persona from session state (set by Module Profil)."""
    return st.session_state.get("persona_content", None)


def load_persona_from_upload():
    """Show file uploader and return persona content if uploaded."""
    uploaded = st.file_uploader(
        "Chargez un profil de communication (.md)",
        type=["md", "txt"],
        help="Fichier genere par le Module Profil & Persona",
    )
    if uploaded:
        content = uploaded.read().decode("utf-8")
        st.session_state.persona_content = content
        return content
    return None


def get_persona():
    """Get persona content from session state, DB, or file upload. Returns content or None."""
    # 1. Session state
    persona = load_persona_from_session()
    if persona:
        return persona

    # 2. DB fallback
    try:
        from db import get_active_profile
        profile = get_active_profile()
        if profile:
            st.session_state.persona_content = profile["persona_content"]
            st.session_state.persona_generated = True
            return profile["persona_content"]
    except ImportError:
        pass

    # 3. Guided navigation + file upload fallback
    st.warning("Aucun profil de communication trouve.")
    st.page_link("pages/1_\U0001f3af_Profil.py", label="Creer votre profil d'abord", icon="\U0001f3af")
    st.caption("Ou chargez un fichier existant :")
    persona = load_persona_from_upload()
    return persona


def load_benchmark_from_session():
    """Try to load benchmark preferences from session state (set by Module Veille)."""
    return st.session_state.get("benchmark_preferences", None)


def load_calendar_from_session():
    """Try to load calendar from session state (set by Module Calendrier)."""
    return st.session_state.get("calendar_content", None)


def save_to_data(content, prefix="output", name="agent"):
    """Save content to the data directory with timestamp."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = name.lower().replace(" ", "-")[:30]
    filepath = DATA_DIR / f"{prefix}-{safe_name}-{timestamp}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def compress_persona_for_content(persona_content):
    """Extract only the sections relevant for content generation (reduce tokens ~60%)."""
    if not persona_content:
        return ""

    keep_sections = [
        "PROFIL DE COMMUNICATION",
        "Identite",
        "Voix & Ton", "Voix et Ton", "Voice",
        "Phrases Signatures", "Signature",
        "Piliers de Contenu", "Piliers", "Content Pillars",
        "Strategie Hashtags", "Hashtags",
        "Differentiation", "USP", "Positionnement",
    ]

    lines = persona_content.split("\n")
    result = []
    include = False

    for line in lines:
        stripped = line.strip()
        # Check if this is a heading
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            include = any(s.lower() in heading_text.lower() for s in keep_sections)
            if include:
                result.append(line)
        elif include:
            result.append(line)

    compressed = "\n".join(result).strip()
    # Fallback: if compression removed too much, use truncated original
    if len(compressed) < 200:
        return persona_content[:3000]
    return compressed


def extract_agent_name(persona_content):
    """Extract the agent name from a persona profile."""
    if not persona_content:
        return "agent"
    for line in persona_content.split("\n"):
        if "PROFIL DE COMMUNICATION" in line:
            # Format: ### PROFIL DE COMMUNICATION - [Name]
            parts = line.split(" - ")
            if len(parts) >= 2:
                return parts[-1].strip()
        if "| **Nom**" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                return parts[3].strip()
    return "agent"
