"""Minimal HTML block surgery for Webflow static exports.

The export is machine-generated and structurally regular, so balanced-tag
scanning is reliable here and avoids a parser dependency. Everything works on
raw strings so that byte-for-byte markup (data-w-id attrs, inline IX2 styles)
survives untouched.
"""

import re

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

_TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(/?)>", re.S)


def find_block(html, start):
    """Return (start, end) of the element whose opening tag begins at `start`.

    `end` is exclusive and includes the closing tag.
    """
    m = _TAG.match(html, start)
    if not m:
        raise ValueError("no tag at offset %d: %r" % (start, html[start:start + 60]))
    name = m.group(2).lower()
    if name in VOID or m.group(4):
        return start, m.end()
    depth = 0
    pos = start
    for t in _TAG.finditer(html, start):
        tname = t.group(2).lower()
        if tname != name:
            continue
        if tname in VOID or t.group(4):
            continue
        if t.group(1):
            depth -= 1
            if depth == 0:
                return start, t.end()
        else:
            depth += 1
        pos = t.end()
    raise ValueError("unbalanced <%s> from offset %d (pos %d)" % (name, start, pos))


def open_tag_start(html, pos):
    """Offset of the '<' of the opening tag containing/preceding `pos`."""
    i = html.rfind("<", 0, pos + 1)
    while i > 0 and html[i + 1] == "/":
        i = html.rfind("<", 0, i)
    return i


def find_by_class(html, cls, start=0, end=None):
    """Offset of the opening tag of the first element carrying CSS class `cls`."""
    end = len(html) if end is None else end
    pat = re.compile(r'class="([^"]*)"')
    for m in pat.finditer(html, start, end):
        if cls in m.group(1).split():
            return open_tag_start(html, m.start())
    return -1


def find_bound(html, cls, start=0, end=None):
    """Offset of the CMS-bound element carrying class `cls`.

    Prefers an element that also carries `w-dyn-bind-empty` - Webflow's own
    marker for "this node is filled from the CMS". Several templates reuse a
    class for both static copy and a bound field (e.g. `text-101-white` appears
    as a literal breadcrumb label *and* as the bound item name), so matching the
    marker first is what keeps the right one from being overwritten. Falls back
    to a plain class match for bindings with no marker, such as the hero
    background sections.
    """
    end = len(html) if end is None else end
    pat = re.compile(r'class="([^"]*)"')
    fallback = -1
    for m in pat.finditer(html, start, end):
        parts = m.group(1).split()
        if cls not in parts:
            continue
        if "w-dyn-bind-empty" in parts:
            return open_tag_start(html, m.start())
        if fallback < 0:
            fallback = open_tag_start(html, m.start())
    return fallback


def iter_by_class(html, cls, start=0, end=None):
    end = len(html) if end is None else end
    pat = re.compile(r'class="([^"]*)"')
    for m in pat.finditer(html, start, end):
        if cls in m.group(1).split():
            yield open_tag_start(html, m.start())


def block_by_class(html, cls, start=0, end=None):
    """Return (start, end) of the first element carrying CSS class `cls`."""
    i = find_by_class(html, cls, start, end)
    if i < 0:
        return None
    return find_block(html, i)


# ---------------------------------------------------------------- attributes

def set_attr(tag, name, value):
    """Set/replace an attribute inside a single opening tag string."""
    pat = re.compile(r'(\s%s=")[^"]*(")' % re.escape(name))
    if pat.search(tag):
        return pat.sub(lambda m: m.group(1) + value.replace("\\", "\\\\") + m.group(2), tag, count=1)
    # insert before the closing '>' (or '/>')
    m = re.match(r"<([a-zA-Z][a-zA-Z0-9]*)", tag)
    insert_at = m.end()
    return tag[:insert_at] + ' %s="%s"' % (name, value) + tag[insert_at:]


def del_attr(tag, name):
    return re.sub(r'\s%s="[^"]*"' % re.escape(name), "", tag, count=1)


def get_attr(tag, name):
    m = re.search(r'\s%s="([^"]*)"' % re.escape(name), tag)
    return m.group(1) if m else None


def edit_open_tag(html, start, fn):
    """Apply `fn` to the opening tag starting at `start`; return new html."""
    m = _TAG.match(html, start)
    if not m:
        raise ValueError("no tag at %d" % start)
    return html[:start] + fn(m.group(0)) + html[m.end():]


def drop_class(tag, cls):
    def repl(m):
        parts = [c for c in m.group(1).split() if c != cls]
        return 'class="%s"' % " ".join(parts)
    return re.sub(r'class="([^"]*)"', repl, tag, count=1)


def add_class(tag, cls):
    def repl(m):
        parts = m.group(1).split()
        if cls not in parts:
            parts.append(cls)
        return 'class="%s"' % " ".join(parts)
    if 'class="' in tag:
        return re.sub(r'class="([^"]*)"', repl, tag, count=1)
    return set_attr(tag, "class", cls)


# ------------------------------------------------------------------ content

def set_inner(html, block, content):
    """Replace the inner HTML of the element spanning `block` = (start, end)."""
    s, e = block
    m = _TAG.match(html, s)
    name = m.group(2).lower()
    if name in VOID or m.group(4):
        return html
    close = "</%s>" % m.group(2)
    ce = html.rfind(close, s, e)
    return html[:m.end()] + content + html[ce:]


def inner_span(html, start):
    """(inner_start, inner_end) for the element opening at `start`."""
    s, e = find_block(html, start)
    m = _TAG.match(html, s)
    if m.group(2).lower() in VOID or m.group(4):
        return None
    close = "</%s>" % m.group(2)
    return m.end(), html.rfind(close, s, e)
