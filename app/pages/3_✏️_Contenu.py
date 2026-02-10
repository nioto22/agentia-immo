"""
AgentIA - Module 4: Content Creation
Generates ready-to-publish posts from persona profile and calendar entries.
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
    MODEL_PERSONA,
    inject_css,
    load_prompt,
    chat_with_claude,
    estimate_cost,
    render_sidebar,
    check_api_key,
    get_persona,
    load_benchmark_from_session,
    load_calendar_from_session,
    extract_agent_name,
    save_to_data,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Creation de Contenu",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- INJECT CSS ---
inject_css()

# --- SIDEBAR ---
render_sidebar(
    module_name="Module 4 - Contenu",
    module_help="""
    <p>1. Chargez votre profil de communication</p>
    <p>2. Choisissez plateforme, format, sujet</p>
    <p>3. L'IA genere un post pret a publier</p>
    <p>4. Copiez et publiez !</p>
    """,
)

# --- HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Module 4 - Creation de Contenu</div>
    <h1>\u270f\ufe0f AgentIA</h1>
    <p>Generez des posts prets a publier, adaptes a votre profil</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# --- API KEY CHECK ---
check_api_key()

# --- INIT STATE ---
if "generated_posts" not in st.session_state:
    st.session_state.generated_posts = []
if "content_generating" not in st.session_state:
    st.session_state.content_generating = False

# --- LOAD PERSONA ---
st.markdown("##### 1. Profil de communication")

persona_content = get_persona()

if not persona_content:
    st.stop()

agent_name = extract_agent_name(persona_content)
st.success(f"Profil charge : **{agent_name}**")

with st.expander("Voir le profil complet", expanded=False):
    st.markdown(persona_content)

# --- LOAD CALENDAR (optional) ---
calendar_content = load_calendar_from_session()
if calendar_content:
    st.info("Calendrier editorial detecte en session. Vous pouvez vous en inspirer pour choisir vos sujets.")
    with st.expander("Voir le calendrier", expanded=False):
        st.markdown(calendar_content)

st.markdown("---")

# --- CONTENT OPTIONS ---
st.markdown("##### 2. Parametres du contenu")

col1, col2 = st.columns(2)

with col1:
    platform = st.selectbox(
        "Plateforme",
        options=["Instagram", "LinkedIn", "Facebook"],
        help="La plateforme cible pour ce contenu",
    )

with col2:
    # Adapt format options based on platform
    format_options = {
        "Instagram": ["Post standard", "Carrousel", "Reel", "Story"],
        "LinkedIn": ["Post standard", "Carrousel", "Article"],
        "Facebook": ["Post standard", "Reel", "Story"],
    }
    content_format = st.selectbox(
        "Format",
        options=format_options.get(platform, ["Post standard"]),
        help="Le type de contenu a generer",
    )

# Topic input
topic = st.text_area(
    "Sujet / Theme du contenu",
    placeholder="Ex: 5 erreurs a eviter lors d'un achat immobilier a Lisbonne\nOu: Presentation d'une nouvelle villa avec vue mer a Cascais\nOu: Coulisses d'une journee de visites avec mes clients",
    height=100,
    help="Decrivez le sujet. Plus vous etes precis, meilleur sera le resultat.",
)

# Advanced options
with st.expander("Options avancees", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        content_pillar = st.text_input(
            "Pilier de contenu (optionnel)",
            placeholder="Ex: Education Luxe, Storytelling...",
            help="Si vide, l'IA choisira le pilier le plus adapte au sujet",
        )
    with col_b:
        content_tone = st.selectbox(
            "Ajustement de ton (optionnel)",
            options=[
                "Selon le profil (defaut)",
                "Plus professionnel",
                "Plus decontracte",
                "Plus emotionnel / storytelling",
                "Plus educatif / donnees",
            ],
        )
    specific_instructions = st.text_input(
        "Instructions specifiques (optionnel)",
        placeholder="Ex: Mentionner le quartier Chiado, inclure un prix, parler d'une promo...",
    )

st.markdown("---")

# --- DETERMINE MODEL ---
# Use Sonnet for complex formats (carousels with multi-slide, articles)
# Use Haiku for standard posts, reels, stories
COMPLEX_FORMATS = ["Carrousel", "Article"]
use_sonnet = content_format in COMPLEX_FORMATS
selected_model = MODEL_PERSONA if use_sonnet else MODEL_CONVERSATION
max_tokens = 4096 if use_sonnet else 2048
model_label = "Sonnet" if use_sonnet else "Haiku"

# --- GENERATE BUTTON ---
st.markdown("##### 3. Generation")

if use_sonnet:
    st.caption(f"Format complexe detecte ({content_format}) — utilisation de {model_label} pour une meilleure qualite.")

if st.button(
    f"Generer le contenu ({model_label})",
    type="primary",
    use_container_width=True,
    disabled=st.session_state.content_generating or not topic.strip(),
):
    if not topic.strip():
        st.warning("Veuillez entrer un sujet pour votre contenu.")
        st.stop()

    st.session_state.content_generating = True

    content_prompt = load_prompt("content_generation.md")
    if not content_prompt:
        st.error("Erreur : fichier prompt content_generation.md introuvable.")
        st.session_state.content_generating = False
        st.stop()

    # Build user message
    user_message = f"""Genere un contenu pret a publier avec les parametres suivants :

**Plateforme :** {platform}
**Format :** {content_format}
**Sujet :** {topic.strip()}
**Date de generation :** {datetime.now().strftime('%d/%m/%Y')}
"""
    if content_pillar.strip():
        user_message += f"**Pilier de contenu :** {content_pillar.strip()}\n"

    if content_tone != "Selon le profil (defaut)":
        user_message += f"**Ajustement de ton :** {content_tone}\n"

    if specific_instructions.strip():
        user_message += f"**Instructions specifiques :** {specific_instructions.strip()}\n"

    if calendar_content:
        user_message += f"\n**Contexte calendrier editorial (pour coherence) :**\n{calendar_content[:1500]}\n"

    # Inject benchmark preferences if available
    prefs = load_benchmark_from_session()
    if prefs:
        user_message += f"\n**PREFERENCES DE L'AGENT (Module 1 - Veille) :**\n"
        user_message += f"- Segment : {prefs.get('segment', 'Non defini')}\n"
        user_message += f"- Localisation : {prefs.get('location', 'Non definie')}\n"
        user_message += f"- Experience : {prefs.get('experience', 'Non definie')}\n"
        user_message += f"- Formats preferes : {', '.join(prefs.get('formats_preferes', []))}\n"
        user_message += f"- Piliers prioritaires : {', '.join(prefs.get('piliers_preferes', []))}\n"
        user_message += "\nAdapte le contenu a ce segment et ces preferences.\n"

    user_message += f"\n---\n\n**PROFIL DE COMMUNICATION DE L'AGENT :**\n\n{persona_content}"

    messages = [{"role": "user", "content": user_message}]

    spinner_msg = "AgentIA redige votre contenu..."
    if use_sonnet:
        spinner_msg = "AgentIA redige votre contenu avec Sonnet (qualite maximale)... (20-40 secondes)"
    else:
        spinner_msg = "AgentIA redige votre contenu... (10-20 secondes)"

    with st.spinner(spinner_msg):
        response, error = chat_with_claude(
            messages,
            content_prompt,
            model=selected_model,
            max_tokens=max_tokens,
        )

    st.session_state.content_generating = False

    if error:
        st.error(f"Erreur : {error}")
        st.stop()

    # Store generated post
    post_entry = {
        "platform": platform,
        "format": content_format,
        "topic": topic.strip(),
        "content": response,
        "model": model_label,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    st.session_state.generated_posts.insert(0, post_entry)

    # Auto-save
    save_to_data(response, prefix=f"contenu-{platform.lower()}", name=agent_name)
    st.rerun()


# --- DISPLAY GENERATED POSTS ---
if st.session_state.generated_posts:
    st.markdown("---")
    st.markdown(f"##### Contenus generes ({len(st.session_state.generated_posts)})")

    for i, post in enumerate(st.session_state.generated_posts):
        # Platform badge color
        platform_class = f"platform-{post['platform'].lower()}"
        platform_emoji = {
            "Instagram": "\U0001f4f7",
            "LinkedIn": "\U0001f4bc",
            "Facebook": "\U0001f310",
        }.get(post["platform"], "\U0001f4dd")

        st.markdown(f"""
        <div class="content-card">
            <div class="content-card-header">
                <h4>
                    <span class="platform-badge {platform_class}">{post['platform']}</span>
                    {platform_emoji} {post['format']} — {post['topic'][:60]}{'...' if len(post['topic']) > 60 else ''}
                    <span style="float:right; font-size:0.7rem; color:#999;">{post['model']} | {post['timestamp']}</span>
                </h4>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Display the content
        with st.expander(f"Voir le contenu complet", expanded=(i == 0)):
            st.markdown(post["content"])

            # Action buttons
            col_dl, col_copy = st.columns(2)
            with col_dl:
                st.download_button(
                    label="Telecharger (.md)",
                    data=post["content"],
                    file_name=f"contenu-{post['platform'].lower()}-{post['format'].lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"dl_{i}",
                )
            with col_copy:
                # Extract just the main text content for easy copying
                st.download_button(
                    label="Telecharger texte brut (.txt)",
                    data=post["content"],
                    file_name=f"post-{post['platform'].lower()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"txt_{i}",
                )

    # Batch download
    st.markdown("---")
    col_batch, col_clear = st.columns(2)

    with col_batch:
        all_content = "\n\n" + "=" * 60 + "\n\n"
        all_content = all_content.join(
            [f"# {p['platform']} | {p['format']} | {p['topic']}\n\n{p['content']}" for p in st.session_state.generated_posts]
        )
        st.download_button(
            label=f"Telecharger tous les contenus ({len(st.session_state.generated_posts)})",
            data=all_content,
            file_name=f"tous-contenus-{agent_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            type="primary",
        )

    with col_clear:
        if st.button("Effacer tous les contenus", use_container_width=True):
            st.session_state.generated_posts = []
            st.rerun()

    # Cost summary
    cost, in_tok, out_tok = estimate_cost()
    st.markdown(
        f'<div class="cost-badge">Cout session : ~${cost:.3f} ({in_tok:,} tokens in / {out_tok:,} tokens out)</div>',
        unsafe_allow_html=True,
    )
