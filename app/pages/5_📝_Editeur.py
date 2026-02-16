"""
AgentIA - Module 5: Post Editor
Edit generated posts: text per platform, images, AI image prompts, multi-platform preview.
iRL-tech x EPINEXUS - Feb 2026
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import io
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    APP_TITLE,
    APP_ICON,
    MODEL_CONVERSATION,
    inject_css,
    render_sidebar,
    check_api_key,
    get_persona,
    extract_agent_name,
    chat_with_claude,
    DATA_DIR,
)
from previews import (
    parse_generated_content,
    render_social_preview_from_parts,
)
from db import (
    init_db,
    get_post_by_id,
    save_post_edit,
    get_post_edit,
    get_posts_for_editor,
    get_active_profile,
)

init_db()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=f"{APP_TITLE} - Editeur de Posts",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- INJECT CSS ---
inject_css()

# --- CONSTANTS ---
PLATFORMS = ["Instagram", "LinkedIn", "Facebook"]
CHAR_LIMITS = {"Instagram": 2200, "LinkedIn": 3000, "Facebook": 63206}

IMAGE_SIZES = {
    "Aucun": None,
    "Instagram Post (1080x1350)": (1080, 1350),
    "Instagram Story (1080x1920)": (1080, 1920),
    "LinkedIn Post (1200x628)": (1200, 628),
    "Facebook Post (1200x630)": (1200, 630),
}

_IMAGE_PROMPT_SYSTEM = """Tu es un expert en generation d'images IA. Tu crees des prompts optimises pour Midjourney v7, DALL-E 3, et Stable Diffusion XL.

Regles :
- Chaque prompt doit etre en anglais
- Midjourney : utilise les parametres --ar, --style, --v 7
- DALL-E 3 : prompt descriptif naturel, mention du style et des details
- Stable Diffusion : prompt avec tags, poids, negative prompt

Pour chaque outil, donne :
1. Le prompt exact a copier
2. Les parametres recommandes
3. Une breve instruction d'utilisation (1 ligne)

Reponds en francais pour les instructions, mais les prompts eux-memes sont en anglais."""


# --- SESSION STATE KEYS ---
_EDITOR_KEYS = [
    "editor_post_id",
    "editor_caption_single",
    "editor_caption_Instagram",
    "editor_caption_LinkedIn",
    "editor_caption_Facebook",
    "editor_hashtags",
    "editor_cta",
    "editor_image_bytes",
    "editor_image_filename",
    "editor_image_prompt",
    "editor_preview_stale",
    "editor_post_meta",
    "editor_visual_suggestion",
]


def _clear_editor_state():
    """Reset all editor_* session state keys."""
    for key in _EDITOR_KEYS:
        if key in st.session_state:
            del st.session_state[key]


def _load_post_into_editor(post_id):
    """Load a post into the editor from DB. Checks post_edits first, then parses raw content."""
    _clear_editor_state()

    post = get_post_by_id(post_id)
    if not post:
        st.session_state.editor_post_id = None
        return

    st.session_state.editor_post_id = post_id
    st.session_state.editor_post_meta = {
        "platform": post["platform"],
        "format": post["format"],
        "topic": post["topic"],
        "created_at": post["created_at"],
    }

    # Check for existing edit
    edit = get_post_edit(post_id)

    if edit:
        caption = edit["caption"]
        hashtags = edit["hashtags"]
        cta = edit["cta"]
        platform_captions = edit["platform_captions"]
        st.session_state.editor_image_prompt = edit.get("image_prompt", "")
        # Load image if path exists
        if edit.get("image_path"):
            img_path = Path(edit["image_path"])
            if img_path.exists():
                st.session_state.editor_image_bytes = img_path.read_bytes()
                st.session_state.editor_image_filename = img_path.name
    else:
        parsed = parse_generated_content(post["content"])
        caption = parsed["caption"]
        hashtags = parsed["hashtags"]
        cta = parsed["cta"]
        platform_captions = {}
        st.session_state.editor_visual_suggestion = parsed.get("visual_suggestion", "")

    # Set captions
    st.session_state.editor_caption_single = caption
    for plat in PLATFORMS:
        st.session_state[f"editor_caption_{plat}"] = platform_captions.get(plat, caption)
    st.session_state.editor_hashtags = hashtags
    st.session_state.editor_cta = cta
    st.session_state.editor_preview_stale = True


def _auto_crop_resize(img, target_w, target_h):
    """Center crop and resize an image using Pillow."""
    from PIL import Image

    orig_w, orig_h = img.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        # Image is wider — crop sides
        new_w = int(orig_h * target_ratio)
        left = (orig_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, orig_h))
    elif orig_ratio < target_ratio:
        # Image is taller — crop top/bottom
        new_h = int(orig_w / target_ratio)
        top = (orig_h - new_h) // 2
        img = img.crop((0, top, orig_w, top + new_h))

    img = img.resize((target_w, target_h), Image.LANCZOS)
    return img


def _handle_resize_and_crop(img, target_platform):
    """Resize with interactive cropper or auto center crop."""
    size = IMAGE_SIZES.get(target_platform)
    if not size:
        return img

    target_w, target_h = size
    orig_w, orig_h = img.size

    # Info banner
    st.info(
        f"**{target_platform}** : {orig_w}x{orig_h} → {target_w}x{target_h} "
        f"(ratio {target_w/target_h:.2f}:1)",
        icon="\U0001f4d0",
    )

    crop_mode = st.radio(
        "Mode de recadrage",
        ["Auto (centre)", "Interactif (cropper)"],
        horizontal=True,
        key="editor_crop_mode",
    )

    if crop_mode == "Interactif (cropper)":
        try:
            from streamlit_cropper import st_cropper
            from PIL import Image
            cropped = st_cropper(
                img,
                aspect_ratio=(target_w, target_h),
                box_color="#B87333",
                return_type="image",
            )
            if cropped:
                cropped = cropped.resize((target_w, target_h), Image.LANCZOS)
                return cropped
        except ImportError:
            st.warning("streamlit-cropper non disponible, recadrage auto utilise.")

    return _auto_crop_resize(img, target_w, target_h)


def _get_editor_image_base64():
    """Get editor image as base64 string, or empty string."""
    img_bytes = st.session_state.get("editor_image_bytes")
    if not img_bytes:
        return ""
    return base64.b64encode(img_bytes).decode("utf-8")


def _char_counter_html(current, limit, platform):
    """Return colored character counter HTML."""
    ratio = current / limit if limit > 0 else 0
    if ratio < 0.8:
        color = "#2E7D32"
    elif ratio < 1.0:
        color = "#E65100"
    else:
        color = "#C62828"
    return f'<span style="font-size:0.75rem; color:{color};">{current}/{limit} caracteres ({platform})</span>'


# --- SIDEBAR ---
render_sidebar(
    module_name="Module 5 - Editeur",
    module_help="""
    <p>1. Selectionnez un post dans la sidebar</p>
    <p>2. Editez texte, hashtags, CTA par plateforme</p>
    <p>3. Uploadez ou generez une image</p>
    <p>4. Previsualisation multi-plateforme</p>
    <p>5. Sauvegardez vos modifications</p>
    """,
)

# --- SIDEBAR: Post selection ---
with st.sidebar:
    st.markdown("---")
    st.markdown("##### Vos posts")

    # Filters
    filter_platform = st.selectbox(
        "Plateforme", ["Toutes"] + PLATFORMS, key="editor_filter_platform"
    )
    filter_search = st.text_input(
        "Rechercher un sujet", key="editor_filter_search", placeholder="Mot-cle..."
    )

    # Get active profile for filtering
    profile = get_active_profile()
    profile_id = profile["id"] if profile else None

    posts = get_posts_for_editor(
        limit=50,
        profile_id=profile_id,
        platform=filter_platform if filter_platform != "Toutes" else None,
        search=filter_search if filter_search else None,
    )

    if not posts:
        st.caption("Aucun post trouve. Generez du contenu dans le Module 4.")
    else:
        for p in posts:
            topic_short = p["topic"][:55] + "..." if len(p["topic"]) > 55 else p["topic"]
            date_str = p["created_at"][:10] if p["created_at"] else ""
            plat_lower = p["platform"].lower()

            badge_colors = {
                "instagram": ("background:#fce4ec; color:#c2185b;", "IG"),
                "linkedin": ("background:#e3f2fd; color:#1565c0;", "LI"),
                "facebook": ("background:#e8eaf6; color:#283593;", "FB"),
            }
            badge_style, badge_label = badge_colors.get(plat_lower, ("background:#f0f0f0; color:#666;", "??"))
            edit_badge = ' <span style="background:#E8F5E9; color:#2E7D32; padding:1px 6px; border-radius:4px; font-size:0.6rem; font-weight:600;">EDITE</span>' if p["has_edit"] else ""

            st.markdown(f"""
            <div style="background:#fff; border:1px solid #e8e0d6; border-radius:6px; padding:0.5rem 0.7rem; margin-bottom:0.3rem; font-size:0.8rem;">
                <span style="{badge_style} padding:1px 6px; border-radius:4px; font-size:0.6rem; font-weight:600;">{badge_label}</span>{edit_badge}
                <span style="color:#827568; font-size:0.65rem; float:right;">{date_str}</span>
                <div style="color:#333; margin-top:0.25rem; line-height:1.3;">{topic_short}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Editer", key=f"load_post_{p['id']}"):
                _load_post_into_editor(p["id"])
                st.rerun()

# --- Handle prefill from Module 4 ---
prefill_id = st.session_state.pop("editor_post_id_prefill", None)
if prefill_id and st.session_state.get("editor_post_id") != prefill_id:
    _load_post_into_editor(prefill_id)
    st.rerun()

# --- HEADER ---
st.markdown("""
<div class="agent-header">
    <div class="agent-badge">Module 5 - Editeur de Posts</div>
    <h1>\U0001f4dd AgentIA</h1>
    <p>Editez, personnalisez et previsualisation vos posts avant publication</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# --- API KEY CHECK ---
check_api_key()

# --- LOAD PERSONA ---
persona_content = st.session_state.get("persona_content", None)
if not persona_content:
    try:
        profile_db = get_active_profile()
        if profile_db:
            persona_content = profile_db["persona_content"]
            st.session_state.persona_content = persona_content
    except Exception:
        pass

agent_name = extract_agent_name(persona_content) if persona_content else "Agent"

# --- CHECK IF POST IS SELECTED ---
current_post_id = st.session_state.get("editor_post_id")

if not current_post_id:
    st.info("Selectionnez un post dans la barre laterale pour commencer l'edition.")
    st.caption("Vous pouvez aussi cliquer **Editer ce post** depuis le Module 4 (Creation de Contenu).")
    st.stop()

# --- POST METADATA HEADER ---
meta = st.session_state.get("editor_post_meta", {})
st.markdown(f"""
<div class="content-card" style="margin-bottom:0.5rem;">
    <div class="content-card-header">
        <h4>
            <span class="platform-badge platform-{meta.get('platform', '').lower()}">{meta.get('platform', '')}</span>
            {meta.get('format', '')} — {meta.get('topic', '')[:80]}
            <span style="float:right; font-size:0.7rem; color:#999;">Post #{current_post_id}</span>
        </h4>
    </div>
</div>
""", unsafe_allow_html=True)

# =====================================================
# MAIN EDITOR LAYOUT: 2 columns
# =====================================================
col_edit, col_preview = st.columns([3, 2])

# =====================================================
# LEFT COLUMN: Text Editor + Images
# =====================================================
with col_edit:
    st.markdown("##### Texte du post")

    # --- Mode selector ---
    edit_mode = st.radio(
        "Mode d'edition",
        ["Texte unique (une plateforme)", "Multi-plateforme"],
        horizontal=True,
        key="editor_mode",
    )

    if edit_mode == "Texte unique (une plateforme)":
        selected_platform = st.selectbox(
            "Plateforme cible",
            PLATFORMS,
            index=PLATFORMS.index(meta.get("platform", "Instagram")) if meta.get("platform") in PLATFORMS else 0,
            key="editor_single_platform",
        )
        caption = st.text_area(
            f"Contenu ({selected_platform})",
            value=st.session_state.get("editor_caption_single", ""),
            height=250,
            key="editor_ta_single",
        )
        st.session_state.editor_caption_single = caption
        # Update all platform captions to same value in single mode
        for plat in PLATFORMS:
            st.session_state[f"editor_caption_{plat}"] = caption

        # Character counter
        limit = CHAR_LIMITS.get(selected_platform, 2200)
        st.markdown(_char_counter_html(len(caption), limit, selected_platform), unsafe_allow_html=True)

    else:
        # Multi-platform tabs
        tabs = st.tabs(PLATFORMS)
        for tab_idx, plat in enumerate(PLATFORMS):
            with tabs[tab_idx]:
                cap_key = f"editor_caption_{plat}"
                caption_val = st.text_area(
                    f"Contenu {plat}",
                    value=st.session_state.get(cap_key, ""),
                    height=200,
                    key=f"editor_ta_{plat}",
                )
                st.session_state[cap_key] = caption_val

                limit = CHAR_LIMITS.get(plat, 2200)
                st.markdown(_char_counter_html(len(caption_val), limit, plat), unsafe_allow_html=True)

    # --- Common fields ---
    st.markdown("---")
    col_h, col_c = st.columns(2)
    with col_h:
        hashtags = st.text_input(
            "Hashtags",
            value=st.session_state.get("editor_hashtags", ""),
            key="editor_input_hashtags",
            placeholder="#immobilier #luxe #paris",
        )
        st.session_state.editor_hashtags = hashtags
    with col_c:
        cta = st.text_input(
            "CTA (Call to Action)",
            value=st.session_state.get("editor_cta", ""),
            key="editor_input_cta",
            placeholder="Contactez-moi pour une estimation gratuite",
        )
        st.session_state.editor_cta = cta

    # =====================================================
    # IMAGE SECTION
    # =====================================================
    st.markdown("---")
    st.markdown("##### Image")

    img_tab_upload, img_tab_prompt = st.tabs(["Telecharger une image", "Generer un prompt"])

    with img_tab_upload:
        uploaded_file = st.file_uploader(
            "Choisir une image",
            type=["png", "jpg", "jpeg", "webp"],
            key="editor_file_uploader",
        )

        if uploaded_file:
            from PIL import Image

            img_original = Image.open(uploaded_file)

            resize_option = st.selectbox(
                "Redimensionner pour",
                list(IMAGE_SIZES.keys()),
                key="editor_resize_option",
            )

            if resize_option != "Aucun":
                img_resized = _handle_resize_and_crop(img_original, resize_option)

                # Before / After side by side
                col_before, col_after = st.columns(2)
                with col_before:
                    st.caption(f"Original ({img_original.size[0]}x{img_original.size[1]})")
                    st.image(img_original, use_column_width=True)
                with col_after:
                    st.caption(f"Resultat ({img_resized.size[0]}x{img_resized.size[1]})")
                    st.image(img_resized, use_column_width=True)
                img = img_resized
            else:
                st.image(img_original, caption=f"{uploaded_file.name} ({img_original.size[0]}x{img_original.size[1]})", use_column_width=True)
                img = img_original

            # Store as bytes
            buf = io.BytesIO()
            img_format = "PNG" if uploaded_file.name.lower().endswith(".png") else "JPEG"
            img.save(buf, format=img_format, quality=90)
            st.session_state.editor_image_bytes = buf.getvalue()
            st.session_state.editor_image_filename = uploaded_file.name

        elif st.session_state.get("editor_image_bytes"):
            st.caption("Image chargee en memoire.")
            from PIL import Image
            existing_img = Image.open(io.BytesIO(st.session_state.editor_image_bytes))
            st.image(existing_img, caption=st.session_state.get("editor_image_filename", "image"), use_column_width=True)

            if st.button("Supprimer l'image", key="editor_remove_image"):
                st.session_state.pop("editor_image_bytes", None)
                st.session_state.pop("editor_image_filename", None)
                st.rerun()

    with img_tab_prompt:
        st.caption("Generez des prompts optimises pour Midjourney, DALL-E 3 et Stable Diffusion.")

        # Use the caption for context
        prompt_caption = st.session_state.get("editor_caption_single", "")
        visual_sugg = st.session_state.get("editor_visual_suggestion", "")

        if st.button("Generer les prompts d'image", type="primary", key="editor_gen_prompt"):
            if not prompt_caption.strip():
                st.warning("Ecrivez d'abord le texte du post pour generer un prompt contextuel.")
            else:
                user_msg = f"""Genere des prompts d'image IA pour ce post de reseaux sociaux :

**Plateforme :** {meta.get('platform', 'Instagram')}
**Texte du post :** {prompt_caption[:500]}
**Suggestion visuelle originale :** {visual_sugg}
**Dimensions recommandees :** 1080x1350 (Instagram), 1200x628 (LinkedIn), 1200x630 (Facebook)

Genere 3 prompts optimises : un pour Midjourney v7, un pour DALL-E 3, un pour Stable Diffusion XL.
Pour chaque outil, donne le prompt exact et une instruction d'utilisation."""

                with st.spinner("Generation des prompts d'image..."):
                    response, error = chat_with_claude(
                        [{"role": "user", "content": user_msg}],
                        _IMAGE_PROMPT_SYSTEM,
                        model=MODEL_CONVERSATION,
                        max_tokens=1500,
                    )

                if error:
                    st.error(f"Erreur : {error}")
                elif response:
                    st.session_state.editor_image_prompt = response

        # Display stored prompt
        stored_prompt = st.session_state.get("editor_image_prompt", "")
        if stored_prompt:
            with st.expander("Prompts generes", expanded=True):
                st.markdown(stored_prompt)

                # Extract code blocks for easy copy
                import re
                code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', stored_prompt, re.DOTALL)
                if code_blocks:
                    st.markdown("**Prompts a copier :**")
                    for idx, block in enumerate(code_blocks):
                        st.code(block.strip(), language=None)

    # =====================================================
    # SAVE & EXPORT
    # =====================================================
    st.markdown("---")
    st.markdown("##### Actions")

    col_save, col_dl_text, col_dl_img = st.columns(3)

    with col_save:
        if st.button("Sauvegarder", type="primary", use_container_width=True, key="editor_save"):
            # Determine caption to save
            main_caption = st.session_state.get("editor_caption_single", "")
            plat_captions = {}
            for plat in PLATFORMS:
                plat_captions[plat] = st.session_state.get(f"editor_caption_{plat}", main_caption)

            # Save image to disk if exists
            image_path = ""
            img_bytes = st.session_state.get("editor_image_bytes")
            if img_bytes:
                images_dir = DATA_DIR / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                ext = Path(st.session_state.get("editor_image_filename", "image.png")).suffix or ".png"
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                img_filename = f"post-{current_post_id}-{timestamp}{ext}"
                img_path = images_dir / img_filename
                img_path.write_bytes(img_bytes)
                image_path = str(img_path)

            save_post_edit(
                post_id=current_post_id,
                caption=main_caption,
                hashtags=st.session_state.get("editor_hashtags", ""),
                cta=st.session_state.get("editor_cta", ""),
                image_path=image_path,
                image_prompt=st.session_state.get("editor_image_prompt", ""),
                platform_captions=plat_captions,
            )
            st.success("Post sauvegarde !")

    with col_dl_text:
        # Build markdown export
        export_lines = [f"# {meta.get('platform', '')} — {meta.get('topic', '')}"]
        export_lines.append(f"Format: {meta.get('format', '')}")
        export_lines.append(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        export_lines.append("")

        for plat in PLATFORMS:
            plat_cap = st.session_state.get(f"editor_caption_{plat}", "")
            if plat_cap:
                export_lines.append(f"## {plat}")
                export_lines.append(plat_cap)
                export_lines.append("")

        if st.session_state.get("editor_hashtags"):
            export_lines.append(f"**Hashtags :** {st.session_state.get('editor_hashtags', '')}")
        if st.session_state.get("editor_cta"):
            export_lines.append(f"**CTA :** {st.session_state.get('editor_cta', '')}")

        export_md = "\n".join(export_lines)

        st.download_button(
            label="Telecharger texte (.md)",
            data=export_md,
            file_name=f"post-{current_post_id}-{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            key="editor_dl_md",
        )

    with col_dl_img:
        img_bytes_dl = st.session_state.get("editor_image_bytes")
        st.download_button(
            label="Telecharger image",
            data=img_bytes_dl or b"",
            file_name=st.session_state.get("editor_image_filename", "image.png"),
            mime="image/png",
            use_container_width=True,
            disabled=not img_bytes_dl,
            key="editor_dl_img",
        )

# =====================================================
# RIGHT COLUMN: Preview
# =====================================================
with col_preview:
    st.markdown("##### Apercu")

    if st.button("Rafraichir l'apercu", type="primary", key="editor_refresh_preview"):
        st.session_state.editor_preview_stale = False

    # Get image base64
    img_b64 = _get_editor_image_base64()
    visual_suggestion = st.session_state.get("editor_visual_suggestion", "")

    preview_tabs = st.tabs(PLATFORMS)
    preview_heights = {"Instagram": 820, "LinkedIn": 620, "Facebook": 600}

    for tab_idx, plat in enumerate(PLATFORMS):
        with preview_tabs[tab_idx]:
            plat_caption = st.session_state.get(f"editor_caption_{plat}", "")
            plat_hashtags = st.session_state.get("editor_hashtags", "")
            plat_cta = st.session_state.get("editor_cta", "")

            preview_html = render_social_preview_from_parts(
                platform=plat,
                caption=plat_caption,
                hashtags=plat_hashtags,
                cta=plat_cta,
                visual_suggestion=visual_suggestion,
                agent_name=agent_name,
                image_base64=img_b64,
            )
            h = preview_heights.get(plat, 650)
            components.html(preview_html, height=h, scrolling=True)

# --- FOOTER ---
st.markdown("---")
st.caption("iRL-tech x EPINEXUS | AgentIA v0.3 — Module Editeur")
