"""Markdown → safe HTML helper for offer PDF rendering.

See openspec/changes/offer-edit-and-finalize/design.md::Decision 6 for
the rationale: a tight allowlist prevents layout-breaking or
potentially-dangerous HTML from creeping into the PDF, while keeping
basic formatting (paragraphs, lists, emphasis, code) available to the
user.
"""
from __future__ import annotations

import bleach
import markdown


# Block-level tags only. No links, no images, no inline styles, no script.
_ALLOWED_TAGS = frozenset({
    "p",
    "br",
    "em",
    "strong",
    "ul",
    "ol",
    "li",
    "code",
    "blockquote",
    "h3",
    "h4",
})

# No attributes are allowed on any tag. WeasyPrint inherits the PDF
# stylesheet from the surrounding template, so we do not need class= or
# style= passthrough.
_ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}


def render_markdown_to_safe_html(text: str) -> str:
    """Convert user-supplied Markdown to a sanitized HTML fragment.

    Empty or whitespace-only input returns an empty string so the
    template can skip the block entirely without emitting an empty `<p>`.

    The output is safe to inject into the offer PDF template via Jinja's
    `| safe` filter — the bleach allowlist guarantees no `<script>`,
    `<style>`, inline `style=`, anchors, or images can survive.
    """
    if not text or not text.strip():
        return ""

    html = markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html",
    )
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=[],  # No protocols allowed (no <a>, no <img>)
        strip=True,    # Drop disallowed tags rather than escape them
    )
    return cleaned
