"""
AgentIA - Social Post Preview Renderers
HTML/CSS mockups for Instagram, LinkedIn, and Facebook post previews.
Uses st.components.v1.html() for full HTML rendering (no SVG stripping).
iRL-tech x EPINEXUS - Feb 2026
"""

import re
import html


# ---------------------------------------------------------------------------
# 1a. Parser — auto-parse generated content
# ---------------------------------------------------------------------------

def parse_generated_content(content: str) -> dict:
    """Parse structured AI-generated content into components.

    Expected format from content_generation.md prompt:
        **[CONTENU PRINCIPAL]**
        Le texte...
        **Hashtags :** #tag1 #tag2...
        **CTA :** Appel a l'action
        **Suggestion visuelle :** Description image
        **Notes pour l'agent :** Conseils...

    Returns dict with keys: caption, hashtags, cta, visual_suggestion, notes, raw
    """
    if not content:
        return {
            "caption": "",
            "hashtags": "",
            "cta": "",
            "visual_suggestion": "",
            "notes": "",
            "raw": "",
        }

    raw = content

    def _extract_section(text, start_marker, end_markers):
        """Extract text between start_marker and the first matching end_marker."""
        pattern = re.escape(start_marker) + r'\s*(.*?)\s*(?=' + '|'.join(re.escape(m) for m in end_markers) + r'|\Z)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    markers = [
        "**Hashtags :**",
        "**Hashtags:**",
        "**CTA :**",
        "**CTA:**",
        "**Suggestion visuelle :**",
        "**Suggestion visuelle:**",
        "**Notes pour l'agent :**",
        "**Notes pour l'agent:**",
        "**Notes :**",
        "**Notes:**",
    ]

    all_end_markers = markers + ["---"]

    hashtags = ""
    for m in ["**Hashtags :**", "**Hashtags:**"]:
        hashtags = _extract_section(content, m, all_end_markers)
        if hashtags:
            break

    cta = ""
    for m in ["**CTA :**", "**CTA:**"]:
        cta = _extract_section(content, m, all_end_markers)
        if cta:
            break

    visual_suggestion = ""
    for m in ["**Suggestion visuelle :**", "**Suggestion visuelle:**"]:
        visual_suggestion = _extract_section(content, m, all_end_markers)
        if visual_suggestion:
            break

    notes = ""
    for m in ["**Notes pour l'agent :**", "**Notes pour l'agent:**", "**Notes :**", "**Notes:**"]:
        notes = _extract_section(content, m, all_end_markers)
        if notes:
            break

    caption = ""
    lines = content.split("\n")
    body_start = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("###") or stripped.startswith("####"):
            body_start = idx + 1
        elif stripped.startswith("**Pilier") or stripped.startswith("**Sujet"):
            body_start = idx + 1
        elif stripped == "**[CONTENU PRINCIPAL]**" or stripped == "**[CONTENU]**":
            body_start = idx + 1
            break

    body_end = len(lines)
    for idx in range(body_start, len(lines)):
        stripped = lines[idx].strip()
        if any(stripped.startswith(m.rstrip()) for m in ["**Hashtags", "**CTA", "**Suggestion visuelle", "**Notes pour"]):
            body_end = idx
            break

    caption_lines = lines[body_start:body_end]
    caption = "\n".join(caption_lines).strip()

    caption = re.sub(r'^\*\*\[CONTENU[^\]]*\]\*\*\s*', '', caption)
    caption = caption.strip()

    if not hashtags and caption:
        hashtag_pattern = re.findall(r'(?:^|\s)(#\w+)', caption)
        if len(hashtag_pattern) >= 2:
            hashtag_line_matches = re.findall(r'((?:#\w+\s*){2,})$', caption)
            if hashtag_line_matches:
                hashtags = hashtag_line_matches[0].strip()
                caption = caption[:caption.rfind(hashtags)].strip()

    if not caption:
        caption = raw

    return {
        "caption": caption,
        "hashtags": hashtags,
        "cta": cta,
        "visual_suggestion": visual_suggestion,
        "notes": notes,
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """HTML-escape text for safe rendering."""
    return html.escape(text) if text else ""


def _initials(name: str) -> str:
    """Get 1-2 letter initials from a name."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][0].upper()
    return "A"


def _truncate(text: str, max_len: int = 300) -> str:
    """Truncate text and add ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "... plus"


def _truncate_visual(text: str, max_len: int = 120) -> str:
    """Truncate visual suggestion for the placeholder box."""
    if not text:
        return "Image du post"
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


# ---------------------------------------------------------------------------
# 1b. Instagram Feed Preview
# ---------------------------------------------------------------------------

def render_instagram_preview(username: str, caption: str, hashtags: str, visual_suggestion: str, display_name: str = "") -> str:
    """Render an Instagram feed post mockup as full HTML document for st.components.v1.html()."""
    initials = _initials(display_name) if display_name else _initials(username)
    caption_display = _esc(_truncate(caption))
    hashtags_display = _esc(hashtags)
    visual_text = _esc(_truncate_visual(visual_suggestion))

    hashtags_html = ""
    if hashtags_display:
        hashtags_html = f'<div style="padding: 0 14px 8px; font-size:14px; color:#00376b; line-height:1.5;">{hashtags_display}</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
</style></head><body>
<div style="max-width:468px; background:#fff; border:1px solid #dbdbdb; border-radius:8px; overflow:hidden; margin:0 auto;">
    <div style="display:flex; align-items:center; padding:12px 14px; gap:10px;">
        <div style="width:32px; height:32px; border-radius:50%; background:linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:13px;">{initials}</div>
        <div>
            <div style="font-weight:600; font-size:14px; color:#262626;">{_esc(username)}</div>
            <div style="font-size:11px; color:#8e8e8e;">Paris, France</div>
        </div>
    </div>
    <div style="width:100%; aspect-ratio:4/5; background:linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045); display:flex; align-items:center; justify-content:center; padding:2rem;">
        <div style="color:rgba(255,255,255,0.9); font-size:13px; text-align:center; max-width:80%; line-height:1.5; background:rgba(0,0,0,0.25); padding:16px 20px; border-radius:12px;">
            <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; opacity:0.7;">Suggestion visuelle</div>
            {visual_text}
        </div>
    </div>
    <div style="padding:8px 12px; display:flex; justify-content:space-between; align-items:center; font-size:22px;">
        <div style="display:flex; gap:14px;">
            <span>\u2661</span><span>\U0001f4ac</span><span>\u27a4</span>
        </div>
        <span>\U0001f516</span>
    </div>
    <div style="padding:0 14px 4px; font-weight:600; font-size:14px; color:#262626;">127 J&apos;aime</div>
    <div style="padding:0 14px 8px; font-size:14px; color:#262626; line-height:1.5;">
        <span style="font-weight:600;">{_esc(username)}</span> {caption_display}
    </div>
    {hashtags_html}
    <div style="padding:0 14px 12px; font-size:10px; color:#8e8e8e; text-transform:uppercase; letter-spacing:0.02em;">Maintenant</div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# 1c. LinkedIn Post Preview
# ---------------------------------------------------------------------------

def render_linkedin_preview(name: str, headline: str, caption: str, hashtags: str, visual_suggestion: str) -> str:
    """Render a LinkedIn post mockup as full HTML document."""
    initials = _initials(name)
    caption_display = _esc(_truncate(caption, 400))
    hashtags_display = _esc(hashtags)
    visual_text = _esc(_truncate_visual(visual_suggestion))

    hashtags_html = ""
    if hashtags_display:
        hashtags_html = f'<div style="padding:0 16px 12px; font-size:14px; color:#0a66c2; line-height:1.5;">{hashtags_display}</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
</style></head><body>
<div style="max-width:552px; background:#fff; border:1px solid #e0e0e0; border-radius:8px; overflow:hidden; margin:0 auto;">
    <div style="display:flex; align-items:flex-start; padding:12px 16px; gap:10px;">
        <div style="width:48px; height:48px; border-radius:50%; flex-shrink:0; background:#0a66c2; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:18px;">{initials}</div>
        <div style="flex:1; min-width:0;">
            <div style="font-weight:600; font-size:14px; color:#000000E6;">{_esc(name)}</div>
            <div style="font-size:12px; color:#00000099; line-height:1.4;">{_esc(headline)}</div>
            <div style="font-size:12px; color:#00000099;">2h &middot; \U0001f310</div>
        </div>
    </div>
    <div style="padding:0 16px 12px; font-size:14px; color:#000000E6; line-height:1.5; white-space:pre-wrap;">{caption_display}</div>
    {hashtags_html}
    <div style="width:100%; aspect-ratio:1.91/1; background:linear-gradient(135deg, #0a66c2, #004182); display:flex; align-items:center; justify-content:center; padding:2rem;">
        <div style="color:rgba(255,255,255,0.9); font-size:13px; text-align:center; max-width:80%; line-height:1.5; background:rgba(0,0,0,0.25); padding:16px 20px; border-radius:12px;">
            <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; opacity:0.7;">Suggestion visuelle</div>
            {visual_text}
        </div>
    </div>
    <div style="padding:8px 16px; display:flex; justify-content:space-between; font-size:12px; color:#00000099; border-bottom:1px solid #e0e0e0;">
        <span>\U0001f44d 42 reactions</span>
        <span>8 commentaires &middot; 3 partages</span>
    </div>
    <div style="display:flex; padding:4px 8px; font-size:13px; font-weight:600; color:#00000099;">
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f44d J&apos;aime</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f4ac Commenter</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f501 Partager</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\u2709 Envoyer</div>
    </div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# 1d. Facebook Post Preview
# ---------------------------------------------------------------------------

def render_facebook_preview(name: str, caption: str, hashtags: str, visual_suggestion: str) -> str:
    """Render a Facebook post mockup as full HTML document."""
    initials = _initials(name)
    caption_display = _esc(_truncate(caption, 400))
    hashtags_display = _esc(hashtags)
    visual_text = _esc(_truncate_visual(visual_suggestion))

    hashtags_html = ""
    if hashtags_display:
        hashtags_html = f'<div style="padding:0 16px 12px; font-size:15px; color:#385898; line-height:1.5;">{hashtags_display}</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
</style></head><body>
<div style="max-width:500px; background:#fff; border:1px solid #dddfe2; border-radius:8px; overflow:hidden; margin:0 auto;">
    <div style="display:flex; align-items:center; padding:12px 16px; gap:10px;">
        <div style="width:40px; height:40px; border-radius:50%; background:#1877F2; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:16px;">{initials}</div>
        <div>
            <div style="font-weight:600; font-size:15px; color:#050505;">{_esc(name)}</div>
            <div style="font-size:13px; color:#65676b;">2h &middot; \U0001f310 Public</div>
        </div>
    </div>
    <div style="padding:0 16px 12px; font-size:15px; color:#050505; line-height:1.5; white-space:pre-wrap;">{caption_display}</div>
    {hashtags_html}
    <div style="width:100%; aspect-ratio:1.91/1; background:linear-gradient(135deg, #1877F2, #0a4da3); display:flex; align-items:center; justify-content:center; padding:2rem;">
        <div style="color:rgba(255,255,255,0.9); font-size:13px; text-align:center; max-width:80%; line-height:1.5; background:rgba(0,0,0,0.25); padding:16px 20px; border-radius:12px;">
            <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; opacity:0.7;">Suggestion visuelle</div>
            {visual_text}
        </div>
    </div>
    <div style="padding:10px 16px; display:flex; justify-content:space-between; font-size:13px; color:#65676b; border-bottom:1px solid #dddfe2;">
        <span>\U0001f44d 24 reactions</span>
        <span>5 commentaires &middot; 2 partages</span>
    </div>
    <div style="display:flex; padding:4px 8px; font-size:14px; font-weight:600; color:#65676b;">
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f44d J&apos;aime</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f4ac Commenter</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f501 Partager</div>
    </div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# 2. Image-aware previews (from_parts) — used by Module 5 Editor
# ---------------------------------------------------------------------------

def _image_section_html(aspect_ratio, gradient, visual_suggestion, image_base64="", image_mime="image/png"):
    """Render the image section: real image if provided, else gradient placeholder."""
    visual_text = _esc(_truncate_visual(visual_suggestion))

    if image_base64:
        return f"""<div style="width:100%; aspect-ratio:{aspect_ratio}; overflow:hidden; display:flex; align-items:center; justify-content:center; background:#f0f0f0;">
        <img src="data:{image_mime};base64,{image_base64}" style="width:100%; height:100%; object-fit:cover;" />
    </div>"""

    return f"""<div style="width:100%; aspect-ratio:{aspect_ratio}; background:{gradient}; display:flex; align-items:center; justify-content:center; padding:2rem;">
        <div style="color:rgba(255,255,255,0.9); font-size:13px; text-align:center; max-width:80%; line-height:1.5; background:rgba(0,0,0,0.25); padding:16px 20px; border-radius:12px;">
            <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; opacity:0.7;">Suggestion visuelle</div>
            {visual_text}
        </div>
    </div>"""


def render_instagram_preview_from_parts(username, caption, hashtags, visual_suggestion, display_name="", image_base64=""):
    """Render Instagram preview from individual parts (for editor)."""
    initials = _initials(display_name) if display_name else _initials(username)
    caption_display = _esc(_truncate(caption))
    hashtags_display = _esc(hashtags)

    hashtags_html = ""
    if hashtags_display:
        hashtags_html = f'<div style="padding: 0 14px 8px; font-size:14px; color:#00376b; line-height:1.5;">{hashtags_display}</div>'

    image_html = _image_section_html("4/5", "linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045)", visual_suggestion, image_base64)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
</style></head><body>
<div style="max-width:468px; background:#fff; border:1px solid #dbdbdb; border-radius:8px; overflow:hidden; margin:0 auto;">
    <div style="display:flex; align-items:center; padding:12px 14px; gap:10px;">
        <div style="width:32px; height:32px; border-radius:50%; background:linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:13px;">{initials}</div>
        <div>
            <div style="font-weight:600; font-size:14px; color:#262626;">{_esc(username)}</div>
            <div style="font-size:11px; color:#8e8e8e;">Paris, France</div>
        </div>
    </div>
    {image_html}
    <div style="padding:8px 12px; display:flex; justify-content:space-between; align-items:center; font-size:22px;">
        <div style="display:flex; gap:14px;">
            <span>\u2661</span><span>\U0001f4ac</span><span>\u27a4</span>
        </div>
        <span>\U0001f516</span>
    </div>
    <div style="padding:0 14px 4px; font-weight:600; font-size:14px; color:#262626;">127 J&apos;aime</div>
    <div style="padding:0 14px 8px; font-size:14px; color:#262626; line-height:1.5;">
        <span style="font-weight:600;">{_esc(username)}</span> {caption_display}
    </div>
    {hashtags_html}
    <div style="padding:0 14px 12px; font-size:10px; color:#8e8e8e; text-transform:uppercase; letter-spacing:0.02em;">Maintenant</div>
</div>
</body></html>"""


def render_linkedin_preview_from_parts(name, headline, caption, hashtags, visual_suggestion, image_base64=""):
    """Render LinkedIn preview from individual parts (for editor)."""
    initials = _initials(name)
    caption_display = _esc(_truncate(caption, 400))
    hashtags_display = _esc(hashtags)

    hashtags_html = ""
    if hashtags_display:
        hashtags_html = f'<div style="padding:0 16px 12px; font-size:14px; color:#0a66c2; line-height:1.5;">{hashtags_display}</div>'

    image_html = _image_section_html("1.91/1", "linear-gradient(135deg, #0a66c2, #004182)", visual_suggestion, image_base64)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
</style></head><body>
<div style="max-width:552px; background:#fff; border:1px solid #e0e0e0; border-radius:8px; overflow:hidden; margin:0 auto;">
    <div style="display:flex; align-items:flex-start; padding:12px 16px; gap:10px;">
        <div style="width:48px; height:48px; border-radius:50%; flex-shrink:0; background:#0a66c2; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:18px;">{initials}</div>
        <div style="flex:1; min-width:0;">
            <div style="font-weight:600; font-size:14px; color:#000000E6;">{_esc(name)}</div>
            <div style="font-size:12px; color:#00000099; line-height:1.4;">{_esc(headline)}</div>
            <div style="font-size:12px; color:#00000099;">2h &middot; \U0001f310</div>
        </div>
    </div>
    <div style="padding:0 16px 12px; font-size:14px; color:#000000E6; line-height:1.5; white-space:pre-wrap;">{caption_display}</div>
    {hashtags_html}
    {image_html}
    <div style="padding:8px 16px; display:flex; justify-content:space-between; font-size:12px; color:#00000099; border-bottom:1px solid #e0e0e0;">
        <span>\U0001f44d 42 reactions</span>
        <span>8 commentaires &middot; 3 partages</span>
    </div>
    <div style="display:flex; padding:4px 8px; font-size:13px; font-weight:600; color:#00000099;">
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f44d J&apos;aime</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f4ac Commenter</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f501 Partager</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\u2709 Envoyer</div>
    </div>
</div>
</body></html>"""


def render_facebook_preview_from_parts(name, caption, hashtags, visual_suggestion, image_base64=""):
    """Render Facebook preview from individual parts (for editor)."""
    initials = _initials(name)
    caption_display = _esc(_truncate(caption, 400))
    hashtags_display = _esc(hashtags)

    hashtags_html = ""
    if hashtags_display:
        hashtags_html = f'<div style="padding:0 16px 12px; font-size:15px; color:#385898; line-height:1.5;">{hashtags_display}</div>'

    image_html = _image_section_html("1.91/1", "linear-gradient(135deg, #1877F2, #0a4da3)", visual_suggestion, image_base64)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
</style></head><body>
<div style="max-width:500px; background:#fff; border:1px solid #dddfe2; border-radius:8px; overflow:hidden; margin:0 auto;">
    <div style="display:flex; align-items:center; padding:12px 16px; gap:10px;">
        <div style="width:40px; height:40px; border-radius:50%; background:#1877F2; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:16px;">{initials}</div>
        <div>
            <div style="font-weight:600; font-size:15px; color:#050505;">{_esc(name)}</div>
            <div style="font-size:13px; color:#65676b;">2h &middot; \U0001f310 Public</div>
        </div>
    </div>
    <div style="padding:0 16px 12px; font-size:15px; color:#050505; line-height:1.5; white-space:pre-wrap;">{caption_display}</div>
    {hashtags_html}
    {image_html}
    <div style="padding:10px 16px; display:flex; justify-content:space-between; font-size:13px; color:#65676b; border-bottom:1px solid #dddfe2;">
        <span>\U0001f44d 24 reactions</span>
        <span>5 commentaires &middot; 2 partages</span>
    </div>
    <div style="display:flex; padding:4px 8px; font-size:14px; font-weight:600; color:#65676b;">
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f44d J&apos;aime</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f4ac Commenter</div>
        <div style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; padding:10px 4px;">\U0001f501 Partager</div>
    </div>
</div>
</body></html>"""


def render_social_preview_from_parts(platform, caption, hashtags, cta, visual_suggestion, agent_name, image_base64=""):
    """Dispatch to the correct from_parts preview renderer."""
    name = agent_name or "Agent"
    username = name.lower().replace(" ", ".")

    if platform == "Instagram":
        return render_instagram_preview_from_parts(
            username=username, caption=caption, hashtags=hashtags,
            visual_suggestion=visual_suggestion, display_name=name, image_base64=image_base64,
        )
    elif platform == "LinkedIn":
        return render_linkedin_preview_from_parts(
            name=name, headline="Agent immobilier", caption=caption,
            hashtags=hashtags, visual_suggestion=visual_suggestion, image_base64=image_base64,
        )
    elif platform == "Facebook":
        return render_facebook_preview_from_parts(
            name=name, caption=caption, hashtags=hashtags,
            visual_suggestion=visual_suggestion, image_base64=image_base64,
        )
    else:
        return render_instagram_preview_from_parts(
            username=username, caption=caption, hashtags=hashtags,
            visual_suggestion=visual_suggestion, display_name=name, image_base64=image_base64,
        )


# ---------------------------------------------------------------------------
# 1e. Dispatch function
# ---------------------------------------------------------------------------

def render_social_preview(platform: str, post_content: str, agent_name: str) -> str:
    """Parse content and render the appropriate social preview.

    Args:
        platform: "Instagram", "LinkedIn", or "Facebook"
        post_content: Raw generated content from AI
        agent_name: Name extracted from persona profile

    Returns:
        Full HTML document string for st.components.v1.html()
    """
    parsed = parse_generated_content(post_content)

    name = agent_name or "Agent"
    username = name.lower().replace(" ", ".")

    if platform == "Instagram":
        return render_instagram_preview(
            username=username,
            caption=parsed["caption"],
            hashtags=parsed["hashtags"],
            visual_suggestion=parsed["visual_suggestion"],
            display_name=name,
        )
    elif platform == "LinkedIn":
        headline = "Agent immobilier"
        return render_linkedin_preview(
            name=name,
            headline=headline,
            caption=parsed["caption"],
            hashtags=parsed["hashtags"],
            visual_suggestion=parsed["visual_suggestion"],
        )
    elif platform == "Facebook":
        return render_facebook_preview(
            name=name,
            caption=parsed["caption"],
            hashtags=parsed["hashtags"],
            visual_suggestion=parsed["visual_suggestion"],
        )
    else:
        return render_instagram_preview(
            username=username,
            caption=parsed["caption"],
            hashtags=parsed["hashtags"],
            visual_suggestion=parsed["visual_suggestion"],
            display_name=name,
        )
