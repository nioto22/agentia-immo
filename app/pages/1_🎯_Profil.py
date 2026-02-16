"""
AgentIA - Module 1: Agent Interview & Persona Creation
SaaS Agent Immobilier Communication IA
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    APP_TITLE,
    APP_ICON,
    MODEL_CONVERSATION,
    MODEL_PERSONA,
    inject_css,
    load_prompt,
    chat_with_claude,
    chat_with_claude_stream,
    estimate_cost,
    render_sidebar,
    check_api_key,
    extract_agent_name,
    save_to_data,
    DATA_DIR,
)
from db import init_db, save_profile, get_active_profile

init_db()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Profil & Persona",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- INJECT CSS ---
inject_css()

# --- CONFIG ---
MAX_TOKENS_CONVERSATION = 1024
MAX_TOKENS_PERSONA = 4096
GENERATION_TRIGGER = "[GENERATION_PROFIL]"

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


# --- HELPERS ---

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
        content = msg["content"].replace(GENERATION_TRIGGER, "").strip()
        if content:
            summary_parts.append(f"{role}: {content}")
    return "\n\n".join(summary_parts)


def save_persona(messages, agent_name="agent"):
    """Save the persona to a file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = agent_name.lower().replace(" ", "-")[:30]

    persona_content = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant" and "PROFIL DE COMMUNICATION" in msg["content"]:
            persona_content = msg["content"]
            break

    filepath = DATA_DIR / f"persona-{safe_name}-{timestamp}.md"
    filepath.write_text(persona_content, encoding="utf-8")
    return filepath


def generate_persona_stream(messages):
    """Generate the final persona using Sonnet 4.5 with streaming."""
    persona_prompt = load_prompt("persona_generation.md")
    interview_summary = build_interview_summary(messages)

    generation_messages = [
        {"role": "user", "content": f"Voici l'interview complete. Genere le profil de communication.\n\n---\n\n{interview_summary}"},
    ]

    return chat_with_claude_stream(
        generation_messages,
        persona_prompt,
        model=MODEL_PERSONA,
        max_tokens=MAX_TOKENS_PERSONA,
    )


# --- SIDEBAR ---
render_sidebar(
    module_name="Module 1 - Profil",
    module_help="""
    <p>1. L'IA vous pose ~10 questions</p>
    <p>2. Repondez naturellement</p>
    <p>3. Votre profil est genere automatiquement</p>
    <p>4. Telechargez le resultat</p>
    """,
)


# --- MAIN HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Module 1 - Profil & Persona</div>
    <h1>\U0001f3af AgentIA</h1>
    <p>Creez votre profil de communication immobiliere en 10 minutes</p>
</div>
""", unsafe_allow_html=True)


# --- API KEY CHECK ---
check_api_key()


# --- INIT STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False
if "social_profile" not in st.session_state:
    st.session_state.social_profile = ""
if "persona_generated" not in st.session_state:
    st.session_state.persona_generated = False

# --- RESTORE FROM DB (on refresh) ---
if "persona_content" not in st.session_state:
    db_profile = get_active_profile()
    if db_profile:
        st.session_state.persona_content = db_profile["persona_content"]
        st.session_state.persona_generated = True
        st.session_state.interview_started = True
        if db_profile["interview_messages"]:
            st.session_state.messages = db_profile["interview_messages"]
        if db_profile.get("social_profile"):
            st.session_state.social_profile = db_profile["social_profile"]


# --- PROGRESS BAR ---
if st.session_state.messages:
    progress, current, total = count_interview_progress(st.session_state.messages)

    if st.session_state.persona_generated:
        st.markdown("""
        <div style="background:#F5F0E6;border-radius:8px;padding:0.75rem 1rem;margin:0.5rem 0 1rem;border-left:3px solid #B87333;">
            <div style="color:#9A5F2A;font-size:0.8rem;font-weight:600;">Profil de communication genere !</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#F5F0E6;border-radius:8px;padding:0.75rem 1rem;margin:0.5rem 0 1rem;border-left:3px solid #B87333;">
            <div style="color:#9A5F2A;font-size:0.8rem;font-weight:600;">Interview en cours... ({current}/{total} questions)</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(progress)


# --- DEMO PROFILES (load pre-built personas for demo) ---
if not st.session_state.interview_started and not st.session_state.persona_generated:
    DEMO_DIR = DATA_DIR / "demo"
    DEMO_PROFILES = {
        "\u2014 Choisir un profil demo \u2014": None,
        "Sophie Martin \u2014 Luxe, Paris 6e/7e/16e": "demo-sophie-martin-persona.md",
        "Marc Dupont \u2014 Residentiel, Ile-de-France": "demo-marc-dupont-persona.md",
        "Claire & Thomas Moreau \u2014 Investissement, Lyon": "demo-claire-thomas-moreau-persona.md",
    }

    st.markdown("##### Charger un profil demo")
    st.caption("Chargez un profil pre-construit pour tester les Modules 3 et 4 sans refaire l'interview.")

    demo_choice = st.selectbox(
        "Profil demo",
        list(DEMO_PROFILES.keys()),
        label_visibility="collapsed",
    )

    if demo_choice != "\u2014 Choisir un profil demo \u2014" and DEMO_PROFILES[demo_choice]:
        demo_path = DEMO_DIR / DEMO_PROFILES[demo_choice]
        if demo_path.exists():
            if st.button("Charger ce profil", type="primary", use_container_width=True):
                demo_content = demo_path.read_text(encoding="utf-8")
                st.session_state.persona_content = demo_content
                st.session_state.persona_generated = True
                st.session_state.interview_started = True
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Profil demo charge : **{demo_choice.split(' \u2014 ')[0]}**"},
                    {"role": "assistant", "content": demo_content},
                ]
                # Save demo profile to DB
                demo_name = extract_agent_name(demo_content)
                save_profile(demo_name, demo_content)
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

        initial_content = "Bonjour, je souhaite creer mon profil de communication."
        if st.session_state.social_profile.strip():
            initial_content += f"\n\nVoici mon profil actuel pour contexte :\n\n{st.session_state.social_profile.strip()}"

        initial_msg = [{"role": "user", "content": initial_content}]

        with st.spinner("AgentIA se prepare..."):
            initial_response, error = chat_with_claude(initial_msg, conversation_prompt)
            if error:
                st.error(f"\u26a0\ufe0f {error}")
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
    avatar = "\U0001f916" if msg["role"] == "assistant" else "\U0001f3e0"
    with st.chat_message(msg["role"], avatar=avatar):
        content = msg["content"]
        content = content.replace(GENERATION_TRIGGER, "").strip()
        st.markdown(content)


# --- CHAT INPUT ---
if not st.session_state.persona_generated:
    if prompt := st.chat_input("Votre reponse..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar="\U0001f3e0"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="\U0001f916"):
            with st.spinner(""):
                response, error = chat_with_claude(
                    st.session_state.messages,
                    conversation_prompt,
                )
                if error:
                    st.error(f"\u26a0\ufe0f {error}")
                    st.session_state.messages.pop()
                    st.stop()

                st.session_state.messages.append({"role": "assistant", "content": response})
                display_content = response.replace(GENERATION_TRIGGER, "").strip()
                st.markdown(display_content)

        # Check if interview is done and persona generation should start
        if GENERATION_TRIGGER in response:
            st.info("Generation du profil complet avec Sonnet 4.5...")
            persona_placeholder = st.empty()
            persona_chunks = []
            for chunk in generate_persona_stream(st.session_state.messages):
                persona_chunks.append(chunk)
                persona_placeholder.markdown("".join(persona_chunks))

            persona_response = "".join(persona_chunks)
            if persona_response.startswith("[ERREUR]"):
                st.error(f"\u26a0\ufe0f {persona_response}")
                st.stop()
            st.session_state.messages.append({"role": "assistant", "content": persona_response})
            st.session_state.persona_generated = True
            st.session_state.persona_content = persona_response
            # Save to DB
            agent_name = extract_agent_name(persona_response)
            save_profile(
                agent_name,
                persona_response,
                social_profile=st.session_state.get("social_profile", ""),
                interview_messages=st.session_state.messages,
            )
            st.rerun()


# --- DISPLAY PERSONA + DOWNLOADS (after generation) ---
if st.session_state.persona_generated:
    st.divider()

    persona_content = ""
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and "PROFIL DE COMMUNICATION" in msg["content"]:
            persona_content = msg["content"]
            break

    # Fallback: use session state (loaded from DB or demo)
    if not persona_content:
        persona_content = st.session_state.get("persona_content", "")

    if persona_content:
        st.session_state.persona_content = persona_content
        agent_name = extract_agent_name(persona_content)

        st.markdown(f"""
        <div class="persona-output">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:1rem;">
                <div style="width:48px; height:48px; border-radius:50%; background:linear-gradient(135deg, #B87333, #9A5F2A); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:18px;">
                    {''.join([p[0] for p in agent_name.split()[:2]]).upper() if agent_name != 'agent' else 'A'}
                </div>
                <div>
                    <div style="font-weight:700; font-size:1.1rem; color:#171412;">{agent_name}</div>
                    <div style="font-size:0.8rem; color:#827568;">Profil de communication</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Voir le profil complet", expanded=True):
            st.markdown(persona_content)

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
    st.markdown("**Prochaine etape :** Utilisez ce profil pour generer votre calendrier editorial et vos premiers posts.")

    # Sidebar reset
    with st.sidebar:
        st.divider()
        if st.button("Nouvelle interview", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.interview_started = False
            st.session_state.social_profile = ""
            st.session_state.total_input_tokens = 0
            st.session_state.total_output_tokens = 0
            st.session_state.persona_generated = False
            st.rerun()

    # Auto-save
    save_persona(st.session_state.messages)
