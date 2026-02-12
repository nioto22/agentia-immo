"""
AgentIA - Module 1: Veille & Benchmark
Market intelligence and content preferences for real estate agents.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
from datetime import datetime
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
    save_to_data,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Veille & Benchmark",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- INJECT CSS ---
inject_css()

# --- SIDEBAR ---
render_sidebar(
    module_name="Module 1 - Veille",
    module_help="""
    <p>1. Consultez les chiffres cles du marche</p>
    <p>2. Renseignez votre situation</p>
    <p>3. Choisissez vos preferences de contenu</p>
    <p>4. Generez votre rapport de veille IA</p>
    """,
)

# --- HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Module 1 - Veille & Benchmark</div>
    <h1>\U0001f50d AgentIA</h1>
    <p>Intelligence de marche et preferences de contenu pour votre strategie</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# --- API KEY CHECK ---
check_api_key()

# --- INIT STATE ---
if "benchmark_content" not in st.session_state:
    st.session_state.benchmark_content = None
if "benchmark_generating" not in st.session_state:
    st.session_state.benchmark_generating = False
if "benchmark_preferences" not in st.session_state:
    st.session_state.benchmark_preferences = {}

# =====================================================
# SECTION 1 : Chiffres cles du marche
# =====================================================
st.markdown("##### 1. Chiffres cles du marche")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Agents sans IA", value="72%", delta=None, help="72% des agents independants n'utilisent pas l'IA pour les reseaux sociaux (2025)")
with col2:
    st.metric(label="Engagement IA", value="+30%", delta=None, help="Les agents utilisant l'IA voient +30% d'engagement")
with col3:
    st.metric(label="Impact video", value="+403%", delta=None, help="Les proprietes avec video recoivent 403% plus de demandes")
with col4:
    st.metric(label="Carrousels", value="4.1%", delta=None, help="Taux d'engagement moyen des carrousels Instagram")

st.caption("Sources : Enquete agents independants 2025, etudes engagement reseaux sociaux immobilier")

st.markdown("---")

# =====================================================
# SECTION 2 : Votre situation
# =====================================================
st.markdown("##### 2. Votre situation")

col1, col2 = st.columns(2)
with col1:
    segment = st.selectbox(
        "Segment de marche",
        ["Residentiel", "Luxe", "Investissement", "Commercial"],
        help="Votre specialisation principale",
    )
with col2:
    location = st.text_input(
        "Localisation",
        placeholder="Ex: Paris, Lyon, Bordeaux...",
        help="Votre zone geographique principale",
    )

col3, col4 = st.columns(2)
with col3:
    experience = st.selectbox(
        "Experience",
        ["Debutant (< 2 ans)", "Intermediaire (2-7 ans)", "Expert (7+ ans)"],
        help="Votre niveau d'experience en immobilier",
    )
with col4:
    platforms = st.multiselect(
        "Plateformes actuelles",
        ["Instagram", "LinkedIn", "Facebook", "TikTok", "Aucune"],
        default=["Instagram"],
        help="Les reseaux sociaux que vous utilisez actuellement",
    )

st.markdown("---")

# =====================================================
# SECTION 3 : Preferences de contenu
# =====================================================
st.markdown("##### 3. Preferences de contenu")

st.markdown("**Formats preferes**")
st.caption("Selectionnez les formats de contenu que vous souhaitez privilegier.")

format_options = [
    "Carrousels educatifs",
    "Reels / Videos courtes",
    "Stories interactives",
    "Posts standard",
    "Articles longs",
    "Lives / Tours virtuels",
]
selected_formats = st.multiselect(
    "Formats",
    format_options,
    default=["Carrousels educatifs", "Reels / Videos courtes"],
    label_visibility="collapsed",
)

st.markdown("")
st.markdown("**Piliers de contenu**")
st.caption(
    "La regle 70/30 : 70% de contenu a valeur ajoutee (education, personnalite, communaute) "
    "et 30% promotionnel (annonces, ventes). Choisissez vos piliers prioritaires."
)

pillar_options = [
    "Biens & Proprietes (annonces, visites, staging)",
    "Expertise marche (tendances, prix, guides quartier)",
    "Marque personnelle (coulisses, valeurs, parcours)",
    "Succes clients (temoignages, celebrations, avis)",
    "Communaute & Lifestyle (evenements, restaurants, quartiers)",
]
selected_pillars = st.multiselect(
    "Piliers",
    pillar_options,
    default=[
        "Biens & Proprietes (annonces, visites, staging)",
        "Expertise marche (tendances, prix, guides quartier)",
        "Marque personnelle (coulisses, valeurs, parcours)",
    ],
    label_visibility="collapsed",
)

st.markdown("---")

# =====================================================
# SECTION 4 : Generation du rapport
# =====================================================
st.markdown("##### 4. Rapport de veille personnalise")

# Validate inputs before generation
can_generate = bool(location and location.strip()) and len(selected_formats) > 0 and len(selected_pillars) > 0

if not can_generate:
    missing = []
    if not location or not location.strip():
        missing.append("localisation")
    if len(selected_formats) == 0:
        missing.append("au moins 1 format")
    if len(selected_pillars) == 0:
        missing.append("au moins 1 pilier")
    st.info(f"Renseignez : {', '.join(missing)} pour generer le rapport.")

if st.button(
    "Generer mon rapport de veille",
    type="primary",
    use_container_width=True,
    disabled=st.session_state.benchmark_generating or not can_generate,
):
    st.session_state.benchmark_generating = True

    benchmark_prompt = load_prompt("benchmark_analysis.md")
    if not benchmark_prompt:
        st.error("Erreur : fichier prompt benchmark_analysis.md introuvable.")
        st.session_state.benchmark_generating = False
        st.stop()

    # Build user message with all selections
    platforms_str = ", ".join(platforms) if platforms else "Aucune"
    formats_str = ", ".join(selected_formats)
    pillars_str = ", ".join(selected_pillars)

    user_message = f"""Voici mon profil et mes preferences. Genere mon rapport de veille personnalise.

**Segment :** {segment}
**Localisation :** {location.strip()}
**Experience :** {experience}
**Plateformes actuelles :** {platforms_str}

**Formats de contenu preferes :** {formats_str}
**Piliers de contenu prioritaires :** {pillars_str}

**Date :** {datetime.now().strftime('%d/%m/%Y')}
"""

    messages = [{"role": "user", "content": user_message}]

    with st.spinner("AgentIA analyse le marche et prepare votre rapport... (15-30 secondes)"):
        response, error = chat_with_claude(
            messages,
            benchmark_prompt,
            model=MODEL_CONVERSATION,
            max_tokens=4096,
        )

    st.session_state.benchmark_generating = False

    if error:
        st.error(f"Erreur : {error}")
        st.stop()

    # Save to session state
    st.session_state.benchmark_content = response
    st.session_state.benchmark_preferences = {
        "segment": segment,
        "location": location.strip(),
        "experience": experience,
        "platforms": platforms,
        "formats_preferes": selected_formats,
        "piliers_preferes": selected_pillars,
    }

    # Auto-save
    safe_location = location.strip().lower().replace(" ", "-")[:20] if location else "agent"
    save_to_data(response, prefix="veille", name=safe_location)
    st.rerun()


# =====================================================
# SECTION 5 : Affichage du resultat
# =====================================================
if st.session_state.benchmark_content:
    st.markdown("---")
    st.markdown("##### Votre rapport de veille")

    st.markdown(f'<div class="persona-output">\n\n{st.session_state.benchmark_content}\n\n</div>', unsafe_allow_html=True)

    st.markdown("")

    # Download & regenerate
    col1, col2 = st.columns(2)
    with col1:
        safe_name = location.strip().lower().replace(" ", "-")[:20] if location and location.strip() else "agent"
        st.download_button(
            label="Telecharger le rapport (.md)",
            data=st.session_state.benchmark_content,
            file_name=f"veille-{safe_name}-{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            type="primary",
        )
    with col2:
        if st.button("Regenerer le rapport", use_container_width=True):
            st.session_state.benchmark_content = None
            st.rerun()

    # Cost badge
    cost, in_tok, out_tok = estimate_cost()
    st.markdown(
        f'<div class="cost-badge">Cout session : ~${cost:.3f} ({in_tok:,} tokens in / {out_tok:,} tokens out)</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "**Prochaine etape :** Utilisez le Module 2 (Profil & Persona) pour creer "
        "votre profil de communication personnalise base sur ces preferences."
    )
