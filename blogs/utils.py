import nh3

ALLOWED_TAGS = {
    "p", "h2", "h3", "h4", "strong", "em", "u", "s",
    "ul", "ol", "li", "a", "blockquote",
    "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
    "code", "pre", "hr", "br", "span", "iframe",
}

ALLOWED_ATTRS = {
    "a":      {"href", "title", "target"},
    "img":    {"src", "alt", "width", "height", "loading", "style"},
    "p":      {"style"},
    "iframe": {"src", "width", "height", "allowfullscreen", "frameborder"},
}

_SAFE_STYLE_PROPS = {"text-align", "float"}

def _attribute_filter(tag, attr, value):
    if attr != "style":
        return value
    kept = []
    for decl in value.split(";"):
        if ":" not in decl:
            continue
        prop, val = (p.strip() for p in decl.split(":", 1))
        if prop.lower() in _SAFE_STYLE_PROPS:
            kept.append(f"{prop}:{val}")
    return "; ".join(kept) if kept else None

def clean_blog_content(raw_html: str) -> str:
    if not raw_html:
        return raw_html
    return nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        attribute_filter=_attribute_filter,
        strip_comments=True,
    )