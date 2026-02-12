"""
AgentIA - Module 4: Content Creation
Generates ready-to-publish posts from persona profile and calendar entries.
Visual calendar picker: select a day to pre-fill content parameters.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import json
import re
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

# --- CALENDAR CARD CSS (shared with Module 3) ---
CARD_CSS = """
<style>
    .mc {
        background: #FFFFFF; border-radius: 12px; overflow: hidden;
        border: 1px solid #e8e0d6; margin-bottom: 0.25rem;
    }
    .mc-rest {
        background: #FFFFFF; border-radius: 12px; overflow: hidden;
        border: 1px dashed #ddd; margin-bottom: 0.25rem; opacity: 0.5;
    }
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
    .mc-plat {
        display: inline-block; padding: 2px 8px; border-radius: 100px;
        font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .mc-plat-instagram { background: #fce4ec; color: #c2185b; }
    .mc-plat-linkedin { background: #e3f2fd; color: #1565c0; }
    .mc-plat-facebook { background: #e8eaf6; color: #283593; }
    .mc-fmt {
        display: inline-block; padding: 2px 8px; border-radius: 100px;
        font-size: 0.65rem; font-weight: 600; background: #F5F0E6; color: #9A5F2A;
    }
    .mc-body {
        padding: 0 0.85rem 0.5rem; font-size: 0.78rem; color: #444; line-height: 1.4;
        border-top: 1px solid #f0ece6;
    }
    .mc-foot {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.35rem 0.85rem; background: #fafaf8; font-size: 0.65rem; color: #827568;
    }
    .mc-pillar {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.6rem; font-weight: 600; color: #fff;
    }
    .legend-row {
        display: flex; gap: 0.75rem; flex-wrap: wrap;
        font-size: 0.7rem; color: #827568; margin-bottom: 0.75rem;
    }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .legend-dot { width: 10px; height: 10px; border-radius: 3px; }
    .week-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.05rem; font-weight: 700; color: #171412;
        padding-bottom: 0.4rem; border-bottom: 2px solid #B87333;
        margin: 1.25rem 0 0.75rem;
    }
    .week-title:first-child { margin-top: 0; }
    .stories-box {
        background: #F5F0E6; border-radius: 8px; padding: 0.75rem 1rem;
        margin-top: 0.75rem; border-left: 3px solid #B87333;
        font-size: 0.78rem; color: #524b46;
    }
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

# --- PILLAR COLORS ---
PILLAR_COLORS = {
    "property": "#E65100",
    "market": "#1565C0",
    "behind": "#6A1B9A",
    "lifestyle": "#2E7D32",
    "success": "#F9A825",
    "default": "#827568",
}

MAX_SUBJECT_LEN = 70

PLATFORMS = ["Instagram", "LinkedIn", "Facebook"]
FORMAT_OPTIONS = {
    "Instagram": ["Post standard", "Carrousel", "Reel", "Story"],
    "LinkedIn": ["Post standard", "Carrousel", "Article"],
    "Facebook": ["Post standard", "Reel", "Story"],
}

# Map calendar format names → closest selectbox option
FORMAT_MAP = {
    "carrousel": "Carrousel",
    "carousel": "Carrousel",
    "reel": "Reel",
    "reels": "Reel",
    "story": "Story",
    "stories": "Story",
    "article": "Article",
    "post": "Post standard",
    "post standard": "Post standard",
    "post texte": "Post standard",
    "post data": "Post standard",
    "video": "Reel",
    "video tour": "Reel",
    "video temoignage": "Reel",
    "infographie": "Post standard",
}


def classify_pillar(pillar_text):
    """Map a pillar name from the AI output to a color key."""
    if not pillar_text:
        return "default"
    p = pillar_text.lower()
    if any(w in p for w in ["property", "propr", "bien", "listing", "imovel", "imoveis"]):
        return "property"
    if any(w in p for w in ["market", "march", "mercado", "insight", "expert", "data"]):
        return "market"
    if any(w in p for w in ["behind", "couliss", "bastidor", "scenes", "personal", "marque"]):
        return "behind"
    if any(w in p for w in ["lifestyle", "life", "commun", "local", "ville", "quartier"]):
        return "lifestyle"
    if any(w in p for w in ["success", "succes", "client", "temoign", "testemunho", "stories"]):
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


def resolve_format(cal_format, platform):
    """Map a calendar format string to the closest selectbox option for a platform."""
    key = cal_format.strip().lower()
    mapped = FORMAT_MAP.get(key, None)
    if not mapped:
        # Fuzzy: check if any key is contained in the format string
        for k, v in FORMAT_MAP.items():
            if k in key:
                mapped = v
                break
    if not mapped:
        mapped = "Post standard"
    # Make sure the mapped format exists for this platform
    available = FORMAT_OPTIONS.get(platform, ["Post standard"])
    if mapped in available:
        return mapped
    return available[0]


def resolve_platform(cal_platform):
    """Normalize platform name to match selectbox options."""
    p = cal_platform.strip().capitalize()
    if p in PLATFORMS:
        return p
    return "Instagram"


def select_calendar_day(day_data):
    """Store selected calendar day in session state and trigger rerun."""
    platform = resolve_platform(day_data.get("platform", "Instagram"))
    fmt = resolve_format(day_data.get("format", ""), platform)
    subject = day_data.get("subject", "")
    pillar = day_data.get("pillar", "")

    st.session_state.prefill_platform = platform
    st.session_state.prefill_format = fmt
    st.session_state.prefill_topic = subject
    st.session_state.prefill_pillar = pillar


def render_calendar_picker(cal_data):
    """Render calendar cards with 'Utiliser' button to pre-fill content params."""

    st.markdown("""
    <div class="legend-row">
        <div class="legend-item"><div class="legend-dot" style="background:#E65100"></div>Biens</div>
        <div class="legend-item"><div class="legend-dot" style="background:#1565C0"></div>Marche</div>
        <div class="legend-item"><div class="legend-dot" style="background:#6A1B9A"></div>Coulisses</div>
        <div class="legend-item"><div class="legend-dot" style="background:#2E7D32"></div>Lifestyle</div>
        <div class="legend-item"><div class="legend-dot" style="background:#F9A825"></div>Succes</div>
    </div>
    """, unsafe_allow_html=True)

    for week_idx, week in enumerate(cal_data.get("weeks", [])):
        week_title = week.get("title", f"Semaine {week_idx + 1}")
        st.markdown(f'<div class="week-title">{week_title}</div>', unsafe_allow_html=True)

        days = week.get("days", [])
        if not days:
            continue

        for row_start in range(0, len(days), 3):
            row_days = days[row_start:row_start + 3]
            cols = st.columns(3)
            for col_idx, day in enumerate(row_days):
                with cols[col_idx]:
                    is_rest = day.get("rest", False)
                    date_str = day.get("date", "")
                    day_num = date_str.split("/")[0].strip() if "/" in date_str else date_str
                    weekday = day.get("weekday", "")
                    platform = day.get("platform", "")
                    fmt = day.get("format", "")
                    subject = day.get("subject", "")
                    pillar = day.get("pillar", "")
                    pillar_key = classify_pillar(pillar)
                    pillar_color = PILLAR_COLORS.get(pillar_key, PILLAR_COLORS["default"])
                    plat_class = f"mc-plat-{platform.lower()}" if platform else ""

                    if is_rest:
                        st.markdown(f"""
                        <div class="mc-rest">
                            <div class="mc-top">
                                <div class="mc-num mc-num-rest">{day_num}</div>
                                <div><div class="mc-weekday">{weekday}</div></div>
                            </div>
                            <div class="mc-body" style="text-align:center; color:#aaa; padding:0.5rem 0.85rem 0.75rem;">
                                Repos
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        subject_short = (subject[:MAX_SUBJECT_LEN] + "...") if len(subject) > MAX_SUBJECT_LEN else subject
                        pillar_html = f'<span class="mc-pillar" style="background:{pillar_color}">{pillar}</span>' if pillar else ""
                        time_slot = day.get("time", "")
                        time_html = f'<span>{time_slot}</span>' if time_slot else "<span></span>"

                        st.markdown(f"""
                        <div class="mc">
                            <div class="mc-top">
                                <div class="mc-num">{day_num}</div>
                                <div>
                                    <div class="mc-weekday">{weekday}</div>
                                    <div class="mc-badges">
                                        <span class="mc-plat {plat_class}">{platform}</span>
                                        <span class="mc-fmt">{fmt}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="mc-body">{subject_short}</div>
                            <div class="mc-foot">
                                {time_html}
                                {pillar_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # "Utiliser" button to pre-fill content params
                        btn_key = f"cal_pick_w{week_idx}_d{row_start + col_idx}"
                        if st.button("Utiliser", key=btn_key, use_container_width=True):
                            select_calendar_day(day)
                            st.rerun()

        # Stories
        stories = week.get("stories", [])
        if stories:
            stories_html = "".join(f"<li>{s}</li>" for s in stories)
            st.markdown(f"""
            <div class="stories-box">
                <strong>Stories de la semaine</strong>
                <ul style="margin:0.3rem 0 0 1rem;">{stories_html}</ul>
            </div>
            """, unsafe_allow_html=True)


# --- SIDEBAR ---
render_sidebar(
    module_name="Module 4 - Contenu",
    module_help="""
    <p>1. Chargez votre profil de communication</p>
    <p>2. Selectionnez un jour du calendrier ou remplissez manuellement</p>
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

# --- LOAD CALENDAR + VISUAL PICKER ---
calendar_content = load_calendar_from_session()
cal_data = None

if calendar_content:
    cal_data = parse_calendar_json(calendar_content)
    if cal_data:
        st.markdown("---")
        st.markdown("##### Calendrier editorial")
        st.caption("Cliquez sur **Utiliser** pour pre-remplir les parametres ci-dessous.")
        with st.expander("Voir le calendrier", expanded=True):
            render_calendar_picker(cal_data)
    else:
        st.info("Calendrier editorial detecte en session.")
        with st.expander("Voir le calendrier (texte)", expanded=False):
            st.markdown(get_markdown_content(calendar_content))

st.markdown("---")

# --- CONTENT OPTIONS (with prefill from calendar) ---
st.markdown("##### 2. Parametres du contenu")

# Read prefill values
prefill_platform = st.session_state.get("prefill_platform", None)
prefill_format = st.session_state.get("prefill_format", None)
prefill_topic = st.session_state.get("prefill_topic", "")
prefill_pillar = st.session_state.get("prefill_pillar", "")

# Platform
platform_index = 0
if prefill_platform and prefill_platform in PLATFORMS:
    platform_index = PLATFORMS.index(prefill_platform)

col1, col2 = st.columns(2)

with col1:
    platform = st.selectbox(
        "Plateforme",
        options=PLATFORMS,
        index=platform_index,
        help="La plateforme cible pour ce contenu",
    )

with col2:
    # Adapt format options based on platform
    available_formats = FORMAT_OPTIONS.get(platform, ["Post standard"])
    format_index = 0
    if prefill_format and prefill_format in available_formats:
        format_index = available_formats.index(prefill_format)

    content_format = st.selectbox(
        "Format",
        options=available_formats,
        index=format_index,
        help="Le type de contenu a generer",
    )

# Topic input (prefilled from calendar)
topic = st.text_area(
    "Sujet / Theme du contenu",
    value=prefill_topic,
    placeholder="Ex: 5 erreurs a eviter lors d'un achat immobilier a Paris\nOu: Presentation d'un appartement haussmannien dans le 7eme\nOu: Coulisses d'une journee de visites avec mes clients",
    height=100,
    help="Decrivez le sujet. Plus vous etes precis, meilleur sera le resultat.",
)

# Advanced options
with st.expander("Options avancees", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        content_pillar = st.text_input(
            "Pilier de contenu (optionnel)",
            value=prefill_pillar,
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
        placeholder="Ex: Mentionner le quartier du Marais, inclure un prix, parler d'une promo...",
    )

st.markdown("---")

# --- DETERMINE MODEL ---
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

    # Clear prefill after generation
    st.session_state.prefill_platform = None
    st.session_state.prefill_format = None
    st.session_state.prefill_topic = ""
    st.session_state.prefill_pillar = ""

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
        md_cal = get_markdown_content(calendar_content) if cal_data else calendar_content
        user_message += f"\n**Contexte calendrier editorial (pour coherence) :**\n{md_cal[:1500]}\n"

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
