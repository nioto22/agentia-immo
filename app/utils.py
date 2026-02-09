"""
AgentIA - Shared Utilities
Common functions used across all modules.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import anthropic
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
APP_TITLE = "AgentIA"
APP_ICON = "\U0001f3e0"
MODEL_CONVERSATION = "claude-haiku-4-5-20251001"   # Fast & cheap for Q&A / structured data
MODEL_PERSONA = "claude-sonnet-4-20250514"          # Quality for complex generation

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DATA_DIR = Path(__file__).parent.parent / "data"

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
</style>
"""


def inject_css():
    """Inject the shared AgentIA CSS theme."""
    st.markdown(AGENTIA_CSS, unsafe_allow_html=True)


def load_prompt(filename):
    """Load a prompt file from the prompts directory."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_client():
    """Get Anthropic client from session state API key."""
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def chat_with_claude(messages, system_prompt, model=None, max_tokens=None):
    """Send messages to Claude and get a response. Returns (text, error)."""
    client = get_client()
    if not client:
        return None, "Configurez votre cle API Anthropic dans la barre laterale."

    model = model or MODEL_CONVERSATION
    max_tokens = max_tokens or 1024
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=api_messages,
        )
        # Track cost
        usage = response.usage
        st.session_state.setdefault("total_input_tokens", 0)
        st.session_state.setdefault("total_output_tokens", 0)
        st.session_state["total_input_tokens"] += usage.input_tokens
        st.session_state["total_output_tokens"] += usage.output_tokens

        return response.content[0].text, None
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e):
            return None, "Credits API insuffisants. Rechargez sur console.anthropic.com > Plans & Billing."
        return None, f"Erreur API : {e}"
    except anthropic.AuthenticationError:
        return None, "Cle API invalide. Verifiez votre cle dans la barre laterale."
    except anthropic.RateLimitError:
        return None, "Limite de requetes atteinte. Reessayez dans quelques secondes."
    except anthropic.APIError as e:
        return None, f"Erreur API Anthropic : {e}"


def estimate_cost():
    """Estimate API cost based on tracked tokens."""
    input_tokens = st.session_state.get("total_input_tokens", 0)
    output_tokens = st.session_state.get("total_output_tokens", 0)
    # Blended estimate (mostly Haiku + some Sonnet calls)
    # Haiku: $0.80/M in, $4/M out | Sonnet: $3/M in, $15/M out
    cost = (input_tokens * 1.5 / 1_000_000) + (output_tokens * 7 / 1_000_000)
    return cost, input_tokens, output_tokens


def render_sidebar(module_name="", module_help=""):
    """Render the shared sidebar with API key config and cost tracking."""
    with st.sidebar:
        st.markdown("### Configuration")

        api_key = st.text_input(
            "Cle API Anthropic",
            type="password",
            value=st.session_state.get("api_key", ""),
            help="Votre cle API Claude (sk-ant-...)",
        )
        if api_key:
            st.session_state.api_key = api_key

        st.divider()

        if module_help:
            st.markdown(f"""
            <div class="sidebar-info">
                <h4>{module_name}</h4>
                {module_help}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="sidebar-info">
            <h4>Modules</h4>
            <p>1. Veille & Benchmark</p>
            <p><strong>2. Profil & Persona</strong></p>
            <p><strong>3. Calendrier Editorial</strong></p>
            <p><strong>4. Creation de Contenu</strong></p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Cost display
        cost, in_tok, out_tok = estimate_cost()
        if in_tok > 0:
            st.caption(f"Tokens: {in_tok:,} in / {out_tok:,} out")
            st.caption(f"Cout estime: ~${cost:.3f}")

        st.divider()
        st.caption("iRL-tech x EPINEXUS | v0.2")


def check_api_key():
    """Check if API key is configured. Stops the page if not."""
    if not st.session_state.get("api_key"):
        st.info("Configurez votre cle API Anthropic dans la barre laterale pour commencer.", icon="\U0001f511")
        st.stop()


def load_persona_from_session():
    """Try to load persona from session state (set by Module 2)."""
    return st.session_state.get("persona_content", None)


def load_persona_from_upload():
    """Show file uploader and return persona content if uploaded."""
    uploaded = st.file_uploader(
        "Chargez un profil de communication (.md)",
        type=["md", "txt"],
        help="Fichier genere par le Module 2 (Profil & Persona)",
    )
    if uploaded:
        content = uploaded.read().decode("utf-8")
        st.session_state.persona_content = content
        return content
    return None


def get_persona():
    """Get persona content from session state or file upload. Returns content or None."""
    persona = load_persona_from_session()
    if persona:
        return persona

    st.warning("Aucun profil de communication en session. Chargez un fichier ou completez d'abord le Module 2.")
    persona = load_persona_from_upload()
    return persona


def load_calendar_from_session():
    """Try to load calendar from session state (set by Module 3)."""
    return st.session_state.get("calendar_content", None)


def save_to_data(content, prefix="output", name="agent"):
    """Save content to the data directory with timestamp."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = name.lower().replace(" ", "-")[:30]
    filepath = DATA_DIR / f"{prefix}-{safe_name}-{timestamp}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath


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
