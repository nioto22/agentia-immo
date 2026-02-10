"""
AgentIA - Module 3: Content Calendar Generation
Generates a personalized 2-week editorial calendar from a persona profile.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent dir to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    APP_TITLE,
    APP_ICON,
    MODEL_CONVERSATION,
    inject_css,
    load_prompt,
    chat_with_claude,
    estimate_cost,
    render_sidebar,
    check_api_key,
    get_persona,
    load_benchmark_from_session,
    extract_agent_name,
    save_to_data,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Calendrier Editorial",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- INJECT CSS ---
inject_css()

# --- SIDEBAR ---
render_sidebar(
    module_name="Module 3 - Calendrier",
    module_help="""
    <p>1. Chargez votre profil de communication</p>
    <p>2. Cliquez sur "Generer le calendrier"</p>
    <p>3. L'IA cree un plan de 14 jours</p>
    <p>4. Telechargez le resultat</p>
    """,
)

# --- HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Module 3 - Calendrier Editorial</div>
    <h1>\U0001f4c5 AgentIA</h1>
    <p>Generez votre calendrier de contenu personnalise pour 2 semaines</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# --- API KEY CHECK ---
check_api_key()

# --- INIT STATE ---
if "calendar_content" not in st.session_state:
    st.session_state.calendar_content = None
if "calendar_generating" not in st.session_state:
    st.session_state.calendar_generating = False

# --- LOAD PERSONA ---
st.markdown("##### 1. Profil de communication")

persona_content = get_persona()

if not persona_content:
    st.stop()

# Show persona summary
agent_name = extract_agent_name(persona_content)
st.success(f"Profil charge : **{agent_name}**")

with st.expander("Voir le profil complet", expanded=False):
    st.markdown(persona_content)

st.markdown("---")

# --- CALENDAR OPTIONS ---
st.markdown("##### 2. Options du calendrier")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Date de debut",
        value=datetime.now().date() + timedelta(days=1),
        help="Le calendrier couvrira 14 jours a partir de cette date",
    )
with col2:
    focus_theme = st.text_input(
        "Theme special (optionnel)",
        placeholder="Ex: Lancement printemps, Nouvelle propriete...",
        help="Un theme ou evenement a integrer dans le calendrier",
    )

st.markdown("---")

# --- GENERATE CALENDAR ---
st.markdown("##### 3. Generation")

if st.button(
    "Generer le calendrier (14 jours)",
    type="primary",
    use_container_width=True,
    disabled=st.session_state.calendar_generating,
):
    st.session_state.calendar_generating = True

    calendar_prompt = load_prompt("calendar_generation.md")
    if not calendar_prompt:
        st.error("Erreur : fichier prompt calendar_generation.md introuvable.")
        st.session_state.calendar_generating = False
        st.stop()

    # Build the user message
    end_date = start_date + timedelta(days=13)
    user_message = f"""Voici le profil de communication de l'agent. Genere un calendrier editorial de 14 jours.

**Periode :** {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}
**Date de generation :** {datetime.now().strftime('%d/%m/%Y')}
"""
    if focus_theme.strip():
        user_message += f"\n**Theme special a integrer :** {focus_theme.strip()}\n"

    # Inject benchmark preferences if available
    prefs = load_benchmark_from_session()
    if prefs:
        user_message += f"\n**PREFERENCES DE L'AGENT (Module 1 - Veille) :**\n"
        user_message += f"- Segment : {prefs.get('segment', 'Non defini')}\n"
        user_message += f"- Localisation : {prefs.get('location', 'Non definie')}\n"
        user_message += f"- Experience : {prefs.get('experience', 'Non definie')}\n"
        user_message += f"- Plateformes : {', '.join(prefs.get('platforms', []))}\n"
        user_message += f"- Formats preferes : {', '.join(prefs.get('formats_preferes', []))}\n"
        user_message += f"- Piliers prioritaires : {', '.join(prefs.get('piliers_preferes', []))}\n"
        user_message += "\nPrivilegie ces formats et piliers dans le calendrier.\n"

    user_message += f"\n---\n\n{persona_content}"

    messages = [{"role": "user", "content": user_message}]

    with st.spinner("AgentIA planifie votre calendrier editorial... (15-30 secondes)"):
        response, error = chat_with_claude(
            messages,
            calendar_prompt,
            model=MODEL_CONVERSATION,
            max_tokens=4096,
        )

    st.session_state.calendar_generating = False

    if error:
        st.error(f"Erreur : {error}")
        st.stop()

    st.session_state.calendar_content = response
    # Auto-save
    save_to_data(response, prefix="calendrier", name=agent_name)
    st.rerun()


# --- DISPLAY CALENDAR ---
if st.session_state.calendar_content:
    st.markdown("---")
    st.markdown("##### Votre calendrier editorial")

    # Display in a styled container
    st.markdown(f'<div class="persona-output">\n\n{st.session_state.calendar_content}\n\n</div>', unsafe_allow_html=True)

    st.markdown("")

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Telecharger le calendrier (.md)",
            data=st.session_state.calendar_content,
            file_name=f"calendrier-{agent_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            type="primary",
        )
    with col2:
        if st.button("Regenerer le calendrier", use_container_width=True):
            st.session_state.calendar_content = None
            st.rerun()

    # Cost
    cost, in_tok, out_tok = estimate_cost()
    st.markdown(
        f'<div class="cost-badge">Cout session : ~${cost:.3f} ({in_tok:,} tokens in / {out_tok:,} tokens out)</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "**Prochaine etape :** Utilisez ce calendrier dans le Module 4 (Creation de Contenu) "
        "pour generer les posts prets a publier."
    )
