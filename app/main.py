"""
AgentIA - Module 2: Agent Interview & Persona Creation
SaaS Agent Immobilier Communication IA
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import anthropic
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
APP_TITLE = "AgentIA"
APP_ICON = "🏠"
MODEL_CONVERSATION = "claude-haiku-4-5-20251001"  # Cheap for Q&A turns
MODEL_PERSONA = "claude-sonnet-4-20250514"  # Quality for final persona
MAX_TOKENS_CONVERSATION = 1024
MAX_TOKENS_PERSONA = 4096
GENERATION_TRIGGER = "[GENERATION_PROFIL]"

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DATA_DIR = Path(__file__).parent.parent / "data"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Communication Immobiliere IA",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS ---
st.markdown("""
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

    .stChatMessage { border-radius: 12px; margin-bottom: 0.5rem; }

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

    .progress-container {
        background: #F5F0E6; border-radius: 8px; padding: 0.75rem 1rem;
        margin: 0.5rem 0 1rem 0; border-left: 3px solid #B87333;
    }
    .progress-text { color: #9A5F2A; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.25rem; }

    .cost-badge {
        background: #f0f0ee; border-radius: 6px; padding: 4px 10px;
        font-size: 0.7rem; color: #827568; display: inline-block; margin-top: 0.5rem;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- HELPERS ---

def load_prompt(filename):
    """Load a prompt file."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_client():
    """Get Anthropic client."""
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def count_interview_progress(messages):
    """Estimate interview progress."""
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    total_questions = 12
    progress = min(len(assistant_msgs) / total_questions, 1.0)
    return progress, len(assistant_msgs), total_questions


def detect_persona_generated(messages):
    """Check if the persona document has been generated."""
    for msg in reversed(messages):
        if msg["role"] == "assistant" and "PROFIL DE COMMUNICATION" in msg["content"]:
            return True
    return False


def detect_generation_trigger(messages):
    """Check if the conversation prompt triggered persona generation."""
    for msg in reversed(messages):
        if msg["role"] == "assistant" and GENERATION_TRIGGER in msg["content"]:
            return True
    return False


def build_interview_summary(messages):
    """Build a compact summary of the interview for the persona generation call."""
    summary_parts = []
    for msg in messages:
        role = "AGENT" if msg["role"] == "user" else "AGENTIA"
        # Skip the generation trigger message
        content = msg["content"].replace(GENERATION_TRIGGER, "").strip()
        if content:
            summary_parts.append(f"{role}: {content}")
    return "\n\n".join(summary_parts)


def save_persona(messages, agent_name="agent"):
    """Save the persona to a file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = agent_name.lower().replace(" ", "-")[:30]

    # Extract persona content
    persona_content = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant" and "PROFIL DE COMMUNICATION" in msg["content"]:
            persona_content = msg["content"]
            break

    filepath = DATA_DIR / f"persona-{safe_name}-{timestamp}.md"
    filepath.write_text(persona_content, encoding="utf-8")
    return filepath


def chat_with_claude(messages, system_prompt, model=None, max_tokens=None):
    """Send messages to Claude and get a response."""
    client = get_client()
    if not client:
        return None, "Configurez votre cle API Anthropic dans la barre laterale."

    model = model or MODEL_CONVERSATION
    max_tokens = max_tokens or MAX_TOKENS_CONVERSATION
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


def generate_persona(messages):
    """Generate the final persona using Sonnet with the full template prompt."""
    persona_prompt = load_prompt("persona_generation.md")
    interview_summary = build_interview_summary(messages)

    generation_messages = [
        {"role": "user", "content": f"Voici l'interview complete. Genere le profil de communication.\n\n---\n\n{interview_summary}"},
    ]

    return chat_with_claude(
        generation_messages,
        persona_prompt,
        model=MODEL_PERSONA,
        max_tokens=MAX_TOKENS_PERSONA,
    )


def estimate_cost():
    """Estimate API cost based on tracked tokens."""
    input_tokens = st.session_state.get("total_input_tokens", 0)
    output_tokens = st.session_state.get("total_output_tokens", 0)
    # Blended estimate (mostly Haiku + one Sonnet call)
    # Haiku: $0.80/M in, $4/M out | Sonnet: $3/M in, $15/M out
    # Rough average
    cost = (input_tokens * 1.5 / 1_000_000) + (output_tokens * 7 / 1_000_000)
    return cost, input_tokens, output_tokens


# --- SIDEBAR ---
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

    st.markdown("""
    <div class="sidebar-info">
        <h4>Comment ca marche</h4>
        <p>1. L'IA vous pose ~10 questions</p>
        <p>2. Repondez naturellement</p>
        <p>3. Votre profil est genere automatiquement</p>
        <p>4. Telechargez le resultat</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sidebar-info">
        <h4>Langue</h4>
        <p>\U0001f1eb\U0001f1f7 Francais</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Cost display
    cost, in_tok, out_tok = estimate_cost()
    if in_tok > 0:
        st.caption(f"Tokens: {in_tok:,} in / {out_tok:,} out")
        st.caption(f"Cout estime: ~${cost:.3f}")

    st.divider()

    if st.button("Nouvelle interview", type="secondary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.interview_started = False
        st.session_state.social_profile = ""
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.session_state.persona_generated = False
        st.rerun()

    st.caption("iRL-tech x EPINEXUS | v0.2")


# --- MAIN HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Module 2 - Profil & Persona</div>
    <h1>🏠 AgentIA</h1>
    <p>Creez votre profil de communication immobiliere en 10 minutes</p>
</div>
""", unsafe_allow_html=True)


# --- INIT STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False
if "social_profile" not in st.session_state:
    st.session_state.social_profile = ""
if "persona_generated" not in st.session_state:
    st.session_state.persona_generated = False


# --- PROGRESS BAR ---
if st.session_state.messages:
    progress, current, total = count_interview_progress(st.session_state.messages)

    if st.session_state.persona_generated:
        st.markdown("""
        <div class="progress-container">
            <div class="progress-text">✅ Profil de communication genere !</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="progress-container">
            <div class="progress-text">Interview en cours... ({current}/{total} questions)</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(progress)


# --- API KEY CHECK ---
if not st.session_state.get("api_key"):
    st.info("Configurez votre cle API Anthropic dans la barre laterale pour commencer.", icon="🔑")
    st.stop()


# --- DEMO PROFILES (load pre-built personas for demo) ---
if not st.session_state.interview_started and not st.session_state.persona_generated:
    DEMO_DIR = DATA_DIR / "demo"
    DEMO_PROFILES = {
        "— Choisir un profil demo —": None,
        "Sophie Martin — Luxe, Paris 6e/7e/16e": "demo-sophie-martin-persona.md",
        "Marc Dupont — Residentiel, Ile-de-France": "demo-marc-dupont-persona.md",
        "Claire & Thomas Moreau — Investissement, Lyon": "demo-claire-thomas-moreau-persona.md",
    }

    st.markdown("##### Charger un profil demo")
    st.caption("Chargez un profil pre-construit pour tester les Modules 3 et 4 sans refaire l'interview.")

    demo_choice = st.selectbox(
        "Profil demo",
        list(DEMO_PROFILES.keys()),
        label_visibility="collapsed",
    )

    if demo_choice != "— Choisir un profil demo —" and DEMO_PROFILES[demo_choice]:
        demo_path = DEMO_DIR / DEMO_PROFILES[demo_choice]
        if demo_path.exists():
            if st.button("Charger ce profil", type="primary", use_container_width=True):
                demo_content = demo_path.read_text(encoding="utf-8")
                st.session_state.persona_content = demo_content
                st.session_state.persona_generated = True
                st.session_state.interview_started = True
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Profil demo charge : **{demo_choice.split(' — ')[0]}**"},
                    {"role": "assistant", "content": demo_content},
                ]
                st.rerun()
        else:
            st.warning(f"Fichier demo introuvable : {demo_path.name}")

    st.markdown("---")
    st.markdown("##### Ou : Commencer une interview")

# --- SOCIAL PROFILE INPUT (before interview starts) ---
if not st.session_state.interview_started:
    st.markdown("##### Accelerez l'interview (optionnel)")
    social_profile = st.text_area(
        "Collez ici votre bio LinkedIn, description Facebook, ou texte de presentation",
        value=st.session_state.social_profile,
        height=100,
        placeholder="Ex: Agent immobilier specialise dans le luxe a Paris depuis 8 ans. Passionne par l'architecture haussmannienne et le design...",
        help="Si fourni, l'IA adaptera ses questions et l'interview sera plus courte (~6-8 questions au lieu de 10-12).",
    )
    st.session_state.social_profile = social_profile

    if st.button("Commencer l'interview", type="primary", use_container_width=True):
        st.session_state.interview_started = True

        conversation_prompt = load_prompt("interview_conversation.md")

        # Build initial message with social profile context if provided
        initial_content = "Bonjour, je souhaite creer mon profil de communication."
        if st.session_state.social_profile.strip():
            initial_content += f"\n\nVoici mon profil actuel pour contexte :\n\n{st.session_state.social_profile.strip()}"

        initial_msg = [{"role": "user", "content": initial_content}]

        with st.spinner("AgentIA se prepare..."):
            initial_response, error = chat_with_claude(initial_msg, conversation_prompt)
            if error:
                st.error(f"⚠️ {error}")
                st.session_state.interview_started = False
                st.stop()
            st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.rerun()

    st.stop()


# --- LOAD PROMPTS ---
conversation_prompt = load_prompt("interview_conversation.md")

# Inject social profile context into system prompt if provided
if st.session_state.social_profile.strip():
    conversation_prompt += f"\n\n## PROFIL SOCIAL FOURNI PAR L'AGENT\n\n{st.session_state.social_profile.strip()}"


# --- DISPLAY MESSAGES ---
for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "🏠"
    with st.chat_message(msg["role"], avatar=avatar):
        content = msg["content"]
        # Clean generation trigger from display
        content = content.replace(GENERATION_TRIGGER, "").strip()
        st.markdown(content)


# --- CHAT INPUT ---
if not st.session_state.persona_generated:
    if prompt := st.chat_input("Votre reponse..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar="🏠"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(""):
                response, error = chat_with_claude(
                    st.session_state.messages,
                    conversation_prompt,
                )
                if error:
                    st.error(f"⚠️ {error}")
                    st.session_state.messages.pop()
                    st.stop()

                st.session_state.messages.append({"role": "assistant", "content": response})
                display_content = response.replace(GENERATION_TRIGGER, "").strip()
                st.markdown(display_content)

        # Check if interview is done and persona generation should start
        if GENERATION_TRIGGER in response:
            with st.spinner("Generation du profil complet avec Sonnet..."):
                persona_response, error = generate_persona(st.session_state.messages)
                if error:
                    st.error(f"⚠️ Erreur generation profil : {error}")
                    st.stop()
                st.session_state.messages.append({"role": "assistant", "content": persona_response})
                st.session_state.persona_generated = True
                # Store persona in session for Modules 3 & 4
                st.session_state.persona_content = persona_response
            st.rerun()


# --- DISPLAY PERSONA + DOWNLOADS (after generation) ---
if st.session_state.persona_generated:
    st.divider()

    # Find persona content
    persona_content = ""
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and "PROFIL DE COMMUNICATION" in msg["content"]:
            persona_content = msg["content"]
            break

    if persona_content:
        # Ensure persona is available for Modules 3 & 4
        st.session_state.persona_content = persona_content

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="Telecharger le profil (.md)",
                data=persona_content,
                file_name=f"profil-communication-{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True,
                type="primary",
            )

        with col2:
            full_transcript = "\n\n".join(
                [f"**{'AgentIA' if m['role'] == 'assistant' else 'Agent'}:** {m['content']}" for m in st.session_state.messages]
            )
            st.download_button(
                label="Telecharger l'interview complete",
                data=full_transcript,
                file_name=f"interview-complete-{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    # Cost summary
    cost, in_tok, out_tok = estimate_cost()
    st.markdown(f'<div class="cost-badge">Cout session : ~${cost:.3f} ({in_tok:,} tokens in / {out_tok:,} tokens out)</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Prochaine etape :** Utilisez ce profil pour generer votre calendrier editorial (Module 3) et vos premiers posts (Module 4).")

    # Auto-save
    save_persona(st.session_state.messages)
