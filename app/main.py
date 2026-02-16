"""
AgentIA - Dashboard (Tableau de Bord)
Central hub showing profile summary, calendar preview, recent posts, and stats.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    APP_TITLE,
    APP_ICON,
    inject_css,
    render_sidebar,
    check_api_key,
)
from db import init_db, get_dashboard_summary, get_edit_count

# --- INIT DB ---
init_db()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Tableau de Bord",
    page_icon=APP_ICON,
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- INJECT CSS ---
inject_css()

# --- SIDEBAR ---
render_sidebar(
    module_name="Tableau de Bord",
    module_help="""
    <p>Vue d'ensemble de votre espace AgentIA</p>
    <p>Profil, calendrier, contenus et statistiques</p>
    """,
)

# --- HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Tableau de Bord</div>
    <h1>\U0001f4ca AgentIA</h1>
    <p>Votre espace de communication immobiliere IA</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# --- API KEY CHECK ---
check_api_key()

# --- LOAD DASHBOARD DATA ---
summary = get_dashboard_summary()

# =====================================================
# SECTION A : Profil
# =====================================================
st.markdown("##### Votre Profil")

if summary["profile"]:
    profile = summary["profile"]
    created = profile["created_at"][:10] if profile["created_at"] else ""

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
        <div class="sidebar-info">
            <h4>Profil Actif</h4>
            <p><strong>{profile['agent_name']}</strong></p>
            <p>Cree le {created}</p>
        </div>
        """, unsafe_allow_html=True)

        if summary["benchmark"]:
            bench = summary["benchmark"]
            st.caption(f"Segment: {bench['segment']} | Localisation: {bench['location']} | Experience: {bench['experience']}")

    with col2:
        st.page_link("pages/1_\U0001f3af_Profil.py", label="Modifier", icon="\U0001f3af", use_container_width=True)
else:
    st.info("Aucun profil de communication cree.")
    st.page_link("pages/1_\U0001f3af_Profil.py", label="Creer votre profil", icon="\U0001f3af", use_container_width=True)

st.markdown("---")

# =====================================================
# SECTION B : Calendrier
# =====================================================
st.markdown("##### Calendrier Editorial")

if summary["calendar"]:
    cal = summary["calendar"]
    cal_created = cal["created_at"][:10] if cal["created_at"] else ""
    theme_info = f" | Theme: {cal['focus_theme']}" if cal.get("focus_theme") else ""

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
        <div class="sidebar-info">
            <h4>Dernier Calendrier</h4>
            <p>Debut: {cal['start_date']}{theme_info}</p>
            <p>Genere le {cal_created}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.page_link("pages/3_\U0001f4c5_Calendrier.py", label="Voir", icon="\U0001f4c5", use_container_width=True)
else:
    st.info("Aucun calendrier editorial genere.")
    if summary["profile"]:
        st.page_link("pages/3_\U0001f4c5_Calendrier.py", label="Generer votre calendrier", icon="\U0001f4c5", use_container_width=True)
    else:
        st.caption("Creez d'abord votre profil pour generer un calendrier.")

st.markdown("---")

# =====================================================
# SECTION C : Posts recents
# =====================================================
st.markdown("##### Posts Recents")

if summary["recent_posts"]:
    for post in summary["recent_posts"]:
        platform_emoji = {
            "Instagram": "\U0001f4f7",
            "LinkedIn": "\U0001f4bc",
            "Facebook": "\U0001f310",
        }.get(post["platform"], "\U0001f4dd")

        post_date = post["created_at"][:10] if post["created_at"] else ""
        topic_short = post["topic"][:70] + "..." if len(post["topic"]) > 70 else post["topic"]

        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e8e0d6;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;">
            <span style="font-size:0.7rem;font-weight:600;text-transform:uppercase;color:#9A5F2A;">{post['platform']}</span>
            <span style="font-size:0.7rem;color:#827568;margin-left:0.5rem;">{post['format']} | {post_date}</span>
            <br/>
            <span style="font-size:0.85rem;color:#333;">{platform_emoji} {topic_short}</span>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        st.page_link("pages/4_\u270f\ufe0f_Contenu.py", label="Creer du contenu", icon="\u270f\ufe0f", use_container_width=True)
else:
    st.info("Aucun contenu genere pour le moment.")
    if summary["profile"]:
        st.page_link("pages/4_\u270f\ufe0f_Contenu.py", label="Generer vos premiers contenus", icon="\u270f\ufe0f", use_container_width=True)
    else:
        st.caption("Creez d'abord votre profil pour generer du contenu.")

st.markdown("---")

# =====================================================
# SECTION D : Statistiques
# =====================================================
st.markdown("##### Statistiques")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Posts generes", value=summary["post_count"])

with col2:
    st.metric(label="Posts edites", value=get_edit_count())

with col3:
    cost_str = f"${summary['total_cost']:.3f}" if summary["total_cost"] > 0 else "$0.000"
    st.metric(label="Cout total API", value=cost_str)

with col4:
    if summary["last_activity"]:
        try:
            last_dt = datetime.fromisoformat(summary["last_activity"])
            last_str = last_dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            last_str = summary["last_activity"][:16]
    else:
        last_str = "Aucune"
    st.metric(label="Derniere activite", value=last_str)

st.markdown("---")

# =====================================================
# SECTION E : Navigation rapide
# =====================================================
st.markdown("##### Modules")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.page_link("pages/1_\U0001f3af_Profil.py", label="Profil", icon="\U0001f3af", use_container_width=True)
with col2:
    st.page_link("pages/2_\U0001f50d_Veille.py", label="Veille", icon="\U0001f50d", use_container_width=True)
with col3:
    st.page_link("pages/3_\U0001f4c5_Calendrier.py", label="Calendrier", icon="\U0001f4c5", use_container_width=True)
with col4:
    st.page_link("pages/4_\u270f\ufe0f_Contenu.py", label="Contenu", icon="\u270f\ufe0f", use_container_width=True)
with col5:
    st.page_link("pages/5_\U0001f4dd_Editeur.py", label="Editeur", icon="\U0001f4dd", use_container_width=True)

st.markdown("")
st.caption("iRL-tech x EPINEXUS | AgentIA v0.3")
