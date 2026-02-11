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
    /* Agenda grid cell */
    .cal-cell {
        background: #FFFFFF; border: 1px solid #e8e0d6; border-radius: 8px;
        padding: 0.5rem; min-height: 120px; position: relative;
        font-family: 'Inter', sans-serif;
    }
    .cal-cell-rest {
        background: #f8f8f6; border: 1px dashed #ddd; border-radius: 8px;
        padding: 0.5rem; min-height: 120px; opacity: 0.6;
        font-family: 'Inter', sans-serif;
    }
    .cal-date {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.3rem; font-weight: 700; color: #B87333; line-height: 1;
    }
    .cal-weekday {
        font-size: 0.6rem; color: #827568; text-transform: uppercase;
        font-weight: 600; letter-spacing: 0.05em;
    }
    .cal-platform {
        display: inline-block; padding: 1px 6px; border-radius: 100px;
        font-size: 0.55rem; font-weight: 700; text-transform: uppercase;
        margin-top: 0.3rem;
    }
    .cal-platform-instagram { background: #fce4ec; color: #c2185b; }
    .cal-platform-linkedin { background: #e3f2fd; color: #1565c0; }
    .cal-platform-facebook { background: #e8eaf6; color: #283593; }
    .cal-format {
        font-size: 0.65rem; color: #B87333; font-weight: 600; margin-top: 0.2rem;
    }
    .cal-subject {
        font-size: 0.62rem; color: #555; line-height: 1.3; margin-top: 0.15rem;
    }
    .cal-pillar-bar {
        position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
        border-radius: 0 0 8px 8px;
    }

    /* Modern card (popover detail) */
    .card-number {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem; font-weight: 700; color: #B87333; line-height: 1;
    }
    .card-pillar-tag {
        display: inline-block; padding: 2px 10px; border-radius: 4px;
        font-size: 0.65rem; font-weight: 600; color: #fff;
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
        font-size: 1rem; font-weight: 700; color: #171412;
        padding-bottom: 0.4rem; border-bottom: 2px solid #B87333;
        margin: 1.25rem 0 0.6rem;
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


def render_visual_calendar(cal_data):
    """Render the visual agenda grid (Option D) with popover detail (Option E)."""

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
        # Week title
        week_title = week.get("title", f"Semaine {week_idx + 1}")
        st.markdown(f'<div class="week-title">{week_title}</div>', unsafe_allow_html=True)

        days = week.get("days", [])
        if not days:
            continue

        # Grid: 7 columns (or fewer if less days)
        num_cols = min(len(days), 7)
        cols = st.columns(num_cols)

        for i, day in enumerate(days[:7]):
            col = cols[i % num_cols]
            is_rest = day.get("rest", False)
            pillar_key = classify_pillar(day.get("pillar", ""))
            pillar_color = PILLAR_COLORS.get(pillar_key, PILLAR_COLORS["default"])
            platform = day.get("platform", "")
            platform_class = f"cal-platform-{platform.lower()}" if platform else ""
            date_str = day.get("date", "")
            # Extract just the day number for the big display
            day_num = date_str.split("/")[0] if "/" in date_str else date_str
            weekday = day.get("weekday", "")

            with col:
                if is_rest:
                    # Rest day — simple display
                    st.markdown(f"""
                    <div class="cal-cell-rest">
                        <div class="cal-weekday">{weekday}</div>
                        <div class="cal-date" style="color:#ccc">{day_num}</div>
                        <div style="text-align:center; color:#aaa; font-size:0.7rem; margin-top:1rem;">Repos</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Compact cell (Option D)
                    subject_short = (day.get("subject", "")[:55] + "...") if len(day.get("subject", "")) > 55 else day.get("subject", "")
                    st.markdown(f"""
                    <div class="cal-cell">
                        <div class="cal-weekday">{weekday}</div>
                        <div class="cal-date">{day_num}</div>
                        <span class="cal-platform {platform_class}">{platform}</span>
                        <div class="cal-format">{day.get("format", "")}</div>
                        <div class="cal-subject">{subject_short}</div>
                        <div class="cal-pillar-bar" style="background:{pillar_color}"></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Popover with Option E detail card
                    with st.popover("Detail", use_container_width=True):
                        # Big number + weekday
                        pcol1, pcol2 = st.columns([1, 3])
                        with pcol1:
                            st.markdown(f'<div class="card-number">{day_num}</div>', unsafe_allow_html=True)
                            st.caption(weekday)
                        with pcol2:
                            if platform:
                                plat_css = platform_class.replace("cal-", "")
                                st.markdown(f'<span class="cal-platform {platform_class}">{platform}</span>', unsafe_allow_html=True)
                            pillar_label = day.get("pillar", "")
                            if pillar_label:
                                st.markdown(f'<span class="card-pillar-tag" style="background:{pillar_color}">{pillar_label}</span>', unsafe_allow_html=True)

                        st.markdown("---")
                        st.markdown(f"**{day.get('format', '')}**")
                        st.markdown(day.get("subject", ""))

                        if day.get("time"):
                            st.caption(f"Horaire : {day['time']}")
                        if day.get("hashtags"):
                            st.caption(f"Hashtags : {day['hashtags']}")

        # Overflow days (if week has more than 7 days)
        if len(days) > 7:
            extra_cols = st.columns(min(len(days) - 7, 7))
            for i, day in enumerate(days[7:]):
                col = extra_cols[i % len(extra_cols)]
                is_rest = day.get("rest", False)
                pillar_key = classify_pillar(day.get("pillar", ""))
                pillar_color = PILLAR_COLORS.get(pillar_key, PILLAR_COLORS["default"])
                platform = day.get("platform", "")
                platform_class = f"cal-platform-{platform.lower()}" if platform else ""
                date_str = day.get("date", "")
                day_num = date_str.split("/")[0] if "/" in date_str else date_str
                weekday = day.get("weekday", "")

                with col:
                    if is_rest:
                        st.markdown(f"""
                        <div class="cal-cell-rest">
                            <div class="cal-weekday">{weekday}</div>
                            <div class="cal-date" style="color:#ccc">{day_num}</div>
                            <div style="text-align:center; color:#aaa; font-size:0.7rem; margin-top:1rem;">Repos</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        subject_short = (day.get("subject", "")[:55] + "...") if len(day.get("subject", "")) > 55 else day.get("subject", "")
                        st.markdown(f"""
                        <div class="cal-cell">
                            <div class="cal-weekday">{weekday}</div>
                            <div class="cal-date">{day_num}</div>
                            <span class="cal-platform {platform_class}">{platform}</span>
                            <div class="cal-format">{day.get("format", "")}</div>
                            <div class="cal-subject">{subject_short}</div>
                            <div class="cal-pillar-bar" style="background:{pillar_color}"></div>
                        </div>
                        """, unsafe_allow_html=True)

                        with st.popover("Detail", use_container_width=True):
                            pcol1, pcol2 = st.columns([1, 3])
                            with pcol1:
                                st.markdown(f'<div class="card-number">{day_num}</div>', unsafe_allow_html=True)
                                st.caption(weekday)
                            with pcol2:
                                if platform:
                                    st.markdown(f'<span class="cal-platform {platform_class}">{platform}</span>', unsafe_allow_html=True)
                                pillar_label = day.get("pillar", "")
                                if pillar_label:
                                    st.markdown(f'<span class="card-pillar-tag" style="background:{pillar_color}">{pillar_label}</span>', unsafe_allow_html=True)
                            st.markdown("---")
                            st.markdown(f"**{day.get('format', '')}**")
                            st.markdown(day.get("subject", ""))
                            if day.get("time"):
                                st.caption(f"Horaire : {day['time']}")
                            if day.get("hashtags"):
                                st.caption(f"Hashtags : {day['hashtags']}")

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
