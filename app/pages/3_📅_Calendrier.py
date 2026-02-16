"""
AgentIA - Module 3: Content Calendar Generation
Generates a personalized 2-week editorial calendar from a persona profile.
Visual display: compact agenda grid + modern card detail on click.
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
    inject_calendar_css,
    load_prompt,
    chat_with_claude_stream,
    estimate_cost,
    render_sidebar,
    check_api_key,
    get_persona,
    load_benchmark_from_session,
    extract_agent_name,
    save_to_data,
    classify_pillar,
    parse_calendar_json,
    get_markdown_content,
    PILLAR_COLORS,
    PILLAR_LABELS,
)
from db import init_db, save_calendar, get_latest_calendar, get_active_profile

init_db()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Calendrier Editorial",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- INJECT CSS ---
inject_css()
inject_calendar_css()

MAX_SUBJECT_LEN = 70


def _render_day_card(day, week_idx, day_idx):
    """Render a single modern card for one day."""
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

    subject_short = (subject[:MAX_SUBJECT_LEN] + "...") if len(subject) > MAX_SUBJECT_LEN else subject
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
        st.markdown(f"**Contenu :** {subject}")
        if time_slot:
            st.markdown(f"**Horaire :** {time_slot}")
        if hashtags:
            st.markdown(f"**Hashtags :** {hashtags}")


def render_visual_calendar(cal_data):
    """Render modern card calendar with 3 cards per row."""

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
                    _render_day_card(day, week_idx, row_start + col_idx)

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

# --- RESTORE FROM DB (on refresh) ---
if st.session_state.calendar_content is None:
    db_cal = get_latest_calendar()
    if db_cal:
        st.session_state.calendar_content = db_cal["calendar_content"]

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

    end_date = start_date + timedelta(days=13)
    user_message = f"""Voici le profil de communication de l'agent. Genere un calendrier editorial de 14 jours.

**Periode :** {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}
**Date de generation :** {datetime.now().strftime('%d/%m/%Y')}
"""
    if focus_theme.strip():
        user_message += f"\n**Theme special a integrer :** {focus_theme.strip()}\n"

    prefs = load_benchmark_from_session()
    if prefs:
        user_message += f"\n**PREFERENCES DE L'AGENT (Module 2 - Veille) :**\n"
        user_message += f"- Segment : {prefs.get('segment', 'Non defini')}\n"
        user_message += f"- Localisation : {prefs.get('location', 'Non definie')}\n"
        user_message += f"- Experience : {prefs.get('experience', 'Non definie')}\n"
        user_message += f"- Plateformes : {', '.join(prefs.get('platforms', []))}\n"
        user_message += f"- Formats preferes : {', '.join(prefs.get('formats_preferes', []))}\n"
        user_message += f"- Piliers prioritaires : {', '.join(prefs.get('piliers_preferes', []))}\n"
        user_message += "\nPrivilegie ces formats et piliers dans le calendrier.\n"

    user_message += f"\n---\n\n{persona_content}"

    messages = [{"role": "user", "content": user_message}]

    st.info("AgentIA planifie votre calendrier editorial...")
    cal_placeholder = st.empty()
    cal_chunks = []
    for chunk in chat_with_claude_stream(
        messages,
        calendar_prompt,
        model=MODEL_CONVERSATION,
        max_tokens=8192,
    ):
        cal_chunks.append(chunk)
        cal_placeholder.markdown("".join(cal_chunks))

    response = "".join(cal_chunks)
    cal_placeholder.empty()
    st.session_state.calendar_generating = False

    if response.startswith("[ERREUR]"):
        st.error(f"Erreur : {response}")
        st.stop()

    st.session_state.calendar_content = response
    save_to_data(get_markdown_content(response), prefix="calendrier", name=agent_name)

    # Save to DB
    profile = get_active_profile()
    profile_id = profile["id"] if profile else None
    save_calendar(profile_id, response, start_date=str(start_date), focus_theme=focus_theme.strip())
    st.rerun()


# --- DISPLAY CALENDAR ---
if st.session_state.calendar_content:
    st.markdown("---")
    st.markdown("##### Votre calendrier editorial")

    cal_data = parse_calendar_json(st.session_state.calendar_content)

    if cal_data:
        render_visual_calendar(cal_data)

        md_content = get_markdown_content(st.session_state.calendar_content)
        with st.expander("Voir la version texte complete", expanded=False):
            st.markdown(md_content)
    else:
        st.warning("Affichage visuel indisponible (donnees structurees non trouvees). Regenerez le calendrier pour obtenir la vue en cartes.")
        st.markdown(
            f'<div class="persona-output">\n\n{st.session_state.calendar_content}\n\n</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

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
