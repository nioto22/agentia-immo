"""
AgentIA - Module 3: Content Calendar Generation
Generates a personalized 2-week editorial calendar from a persona profile.
Visual display: compact agenda grid + modern card detail on click.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import json
import re
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

# --- INJECT CSS + CALENDAR CSS ---
inject_css()

CALENDAR_CSS = """
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
st.markdown(CALENDAR_CSS, unsafe_allow_html=True)


# --- PILLAR COLORS ---
PILLAR_COLORS = {
    "property": "#E65100",
    "market": "#1565C0",
    "behind": "#6A1B9A",
    "lifestyle": "#2E7D32",
    "success": "#F9A825",
    "default": "#827568",
}

PILLAR_LABELS = {
    "property": "Biens & Proprietes",
    "market": "Expertise Marche",
    "behind": "Coulisses",
    "lifestyle": "Lifestyle",
    "success": "Succes Clients",
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
    if any(w in p for w in ["lifestyle", "life", "commun", "local", "lisboa", "quartier"]):
        return "lifestyle"
    if any(w in p for w in ["success", "succes", "client", "temoign", "testemunho", "stories"]):
        return "success"
    return "default"


def parse_calendar_json(content):
    """Extract and parse JSON data from calendar content."""
    match = re.search(r'<!--CALENDAR_JSON\s*(.*?)\s*CALENDAR_JSON-->', content, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return None


def get_markdown_content(content):
    """Return the markdown portion (without the hidden JSON block)."""
    return re.sub(r'<!--CALENDAR_JSON.*?CALENDAR_JSON-->', '', content, flags=re.DOTALL).strip()


MAX_SUBJECT_LEN = 70  # chars shown on card, full text in popover


def _render_day_card(day, week_idx, day_idx):
    """Render a single modern card (Option E) for one day."""
    is_rest = day.get("rest", False)
    date_str = day.get("date", "")
    day_num = date_str.split("/")[0].strip() if "/" in date_str else date_str
    weekday = day.get("weekday", "")
    platform = day.get("platform", "")
    fmt = day.get("format", "")
    subject = day.get("subject", "")
    pillar = day.get("pillar", "")
    time_slot = day.get("time", "")
    hashtags = day.get("hashtags", "")
    pillar_key = classify_pillar(pillar)
    pillar_color = PILLAR_COLORS.get(pillar_key, PILLAR_COLORS["default"])
    plat_class = f"mc-plat-{platform.lower()}" if platform else ""

    if is_rest:
        st.markdown(f"""
        <div class="mc-rest">
            <div class="mc-top">
                <div class="mc-num mc-num-rest">{day_num}</div>
                <div>
                    <div class="mc-weekday">{weekday}</div>
                </div>
            </div>
            <div class="mc-body" style="text-align:center; color:#aaa; padding:0.5rem 0.85rem 0.75rem;">
                Repos — Stories uniquement
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Truncate subject for card
    subject_short = (subject[:MAX_SUBJECT_LEN] + "...") if len(subject) > MAX_SUBJECT_LEN else subject

    # Card HTML
    pillar_html = f'<span class="mc-pillar" style="background:{pillar_color}">{pillar}</span>' if pillar else ""
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

    # Popover with full detail
    with st.popover("Voir le detail", use_container_width=True):
        # Header: big number + meta
        pcol1, pcol2 = st.columns([1, 4])
        with pcol1:
            st.markdown(f'<div class="pop-num">{day_num}</div>', unsafe_allow_html=True)
        with pcol2:
            st.markdown(f"**{weekday}** {date_str}")
            badges_md = ""
            if platform:
                badges_md += f'<span class="mc-plat {plat_class}">{platform}</span> '
            if fmt:
                badges_md += f'<span class="mc-fmt">{fmt}</span> '
            if pillar:
                badges_md += f'<span class="pop-pillar" style="background:{pillar_color}">{pillar}</span>'
            st.markdown(badges_md, unsafe_allow_html=True)

        st.markdown("---")

        # Full subject
        st.markdown(f"**Contenu :** {subject}")

        # Details
        if time_slot:
            st.markdown(f"**Horaire :** {time_slot}")
        if hashtags:
            st.markdown(f"**Hashtags :** {hashtags}")


def render_visual_calendar(cal_data):
    """Render modern card calendar (Option E) with 3 cards per row."""

    # Legend
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

        # Render cards in rows of 3
        for row_start in range(0, len(days), 3):
            row_days = days[row_start:row_start + 3]
            cols = st.columns(3)
            for col_idx, day in enumerate(row_days):
                with cols[col_idx]:
                    _render_day_card(day, week_idx, row_start + col_idx)

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
    module_name="Module 3 - Calendrier",
    module_help="""
    <p>1. Chargez votre profil de communication</p>
    <p>2. Cliquez sur "Generer le calendrier"</p>
    <p>3. Cliquez sur une cellule pour le detail</p>
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
            max_tokens=6144,
        )

    st.session_state.calendar_generating = False

    if error:
        st.error(f"Erreur : {error}")
        st.stop()

    st.session_state.calendar_content = response
    # Auto-save (markdown only, without JSON block)
    save_to_data(get_markdown_content(response), prefix="calendrier", name=agent_name)
    st.rerun()


# --- DISPLAY CALENDAR ---
if st.session_state.calendar_content:
    st.markdown("---")
    st.markdown("##### Votre calendrier editorial")

    # Try to parse JSON for visual display
    cal_data = parse_calendar_json(st.session_state.calendar_content)

    if cal_data:
        # Visual display (Option D grid + Option E popover)
        render_visual_calendar(cal_data)

        # Expandable full markdown version
        md_content = get_markdown_content(st.session_state.calendar_content)
        with st.expander("Voir la version texte complete", expanded=False):
            st.markdown(md_content)
    else:
        # Fallback: render raw markdown (old calendars without JSON)
        st.markdown(
            f'<div class="persona-output">\n\n{st.session_state.calendar_content}\n\n</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        download_content = get_markdown_content(st.session_state.calendar_content) if cal_data else st.session_state.calendar_content
        st.download_button(
            label="Telecharger le calendrier (.md)",
            data=download_content,
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
