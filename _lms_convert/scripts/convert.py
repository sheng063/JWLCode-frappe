#!/usr/bin/env python3
"""Convert LMS exercise HTML statements (with MathML) into legacy-icpc LaTeX.

Provides:
  - MathML -> LaTeX math
  - public-sample extraction (样例输入/样例输出 pairs)
  - stable ASCII problem-id generation from titles
  - full HTML -> LaTeX statement rendering (with image materialization)
"""
import html
import os
import re
import unicodedata
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Problem id generation
# ---------------------------------------------------------------------------


def slug_for_id(title: str, salt: str = "") -> str:
    """Return a stable `^[a-z0-9]+$` id from a title."""
    title = title or ""
    core = re.sub(r"^C\d+\s*[·.:\-~]\s*", "", title).strip()
    core = re.sub(r"\s*\[[0-9]+\]\s*$", "", core).strip()

    out = []
    try:
        from pypinyin import lazy_pinyin

        for ch in core:
            n = unicodedata.normalize("NFKC", ch)
            if n.isascii():
                out.append(n)
            else:
                out.extend(lazy_pinyin(ch, errors="default"))
    except Exception:
        for ch in core:
            if ch.isascii() and ch.isalnum():
                out.append(ch.lower())
    joined = "".join(out).lower()
    joined = re.sub(r"[^a-z0-9]", "", joined)
    if not joined:
        joined = "problem"
    if len(joined) > 32:
        joined = joined[:32]
    if not joined[0].isalpha():
        joined = "p" + joined
    if salt:
        joined = joined + "_" + salt
    return joined


def slug_for_id_unique(title: str, used: set) -> str:
    base = slug_for_id(title)
    cand = base
    i = 1
    while cand in used:
        i += 1
        cand = base + str(i)
    used.add(cand)
    return cand


# ---------------------------------------------------------------------------
# MathML -> LaTeX
# ---------------------------------------------------------------------------

_OPERATOR_MAP = {
    "&lt;": "<",
    "&gt;": ">",
    "≤": r"\le",
    "≥": r"\ge",
    "≠": r"\ne",
    "×": r"\times",
    "÷": r"\div",
    "−": "-",
    "–": "-",
    "—": "-",
    "∼": r"\sim",
    "~": r"\sim",
    "⋯": r"\cdots",
    "…": r"\ldots",
    "∗": "*",
    "≈": r"\approx",
    "·": r"\cdot",
    "\u00a0": " ",
    "\u2009": " ",
}


def _mathml_tree(inner):
    """Parse MathML inner content into a nested node tree.

    Node = ('text', str) | (tag, [children])  ; tags lowercased.
    """
    tag_re = re.compile(r"<(/?)([a-zA-Z]+)([^>]*)>")
    root = ("root", [])
    stack = [root]

    def cur():
        return stack[-1]

    pos = 0
    for mo in tag_re.finditer(inner):
        if mo.start() > pos:
            text = inner[pos : mo.start()]
            if text.strip():
                cur()[1].append(("text", text))
        close, tag = mo.group(1), mo.group(2).lower()
        if close:
            if len(stack) > 1:
                stack.pop()
        else:
            node = (tag, [])
            cur()[1].append(node)
            stack.append(node)
        pos = mo.end()
    if pos < len(inner):
        text = inner[pos:]
        if text.strip():
            cur()[1].append(("text", text))
    return root


def _render_math_node(node):
    """Recursively render a MathML node to a LaTeX math string."""
    kind = node[0]
    if kind == "text":
        t = node[1].replace("\u00a0", " ").replace("\u2009", " ")
        t = html.unescape(t)
        return t
    tag, children = node
    rendered = [_render_math_node(c) for c in children]

    def var_subscript(lst):
        # Merge a bare digit that directly follows a variable: p, 1 -> p_1
        out = []
        for i, part in enumerate(lst):
            out.append(part)
        return "".join(out)

    if tag in ("mrow", "math", "mstyle", "semantics", "root"):
        # handle variable+digit subscript fusion across a flat mrow
        res = []
        for part in rendered:
            if part and part.isdigit() and res and _is_var(res[-1]):
                res[-1] = res[-1] + "_{%s}" % part
            else:
                res.append(part)
        return "".join(res)
    if tag == "mi":
        return rendered[0] if rendered else ""
    if tag == "mn":
        return rendered[0] if rendered else ""
    if tag == "mo":
        return rendered[0] if rendered else ""
    if tag == "mtext":
        return r"\text{" + "".join(rendered) + "}"
    if tag == "msup":
        base = rendered[0] if rendered else ""
        sup = "".join(rendered[1:]) if len(rendered) > 1 else ""
        return base + "^{" + sup + "}"
    if tag == "msub":
        base = rendered[0] if rendered else ""
        sub = "".join(rendered[1:]) if len(rendered) > 1 else ""
        return base + "_{" + sub + "}"
    if tag == "msubsup":
        base = rendered[0] if rendered else ""
        sub = "".join(rendered[1:2]) if len(rendered) > 1 else ""
        sup = "".join(rendered[2:3]) if len(rendered) > 2 else ""
        return base + "_{" + sub + "}^{" + sup + "}"
    if tag == "mfrac":
        num = "".join(rendered[0:1]) if rendered else ""
        den = "".join(rendered[1:2]) if len(rendered) > 1 else ""
        return r"\frac{" + num + "}{" + den + "}"
    if tag == "msqrt":
        return r"\sqrt{" + "".join(rendered) + "}"
    return "".join(rendered)


def _is_var(s):
    # a LaTeX math var token: single ascii letter allowed (may be wrapped in \;)
    return bool(re.fullmatch(r"[a-zA-Z]", s))


def mathml_to_latex(mth: str) -> str:
    """Convert a raw `<math>...</math>` block to inline LaTeX math."""
    inner = re.sub(r"^\s*<math[^>]*>", "", mth, flags=re.I)
    inner = re.sub(r"</math>\s*$", "", inner, flags=re.I)
    tree = _mathml_tree(inner)
    tex = _render_math_node(tree)
    for k, v in _OPERATOR_MAP.items():
        tex = tex.replace(k, v)
    tex = tex.replace("%", r"\%").replace("#", r"\#")
    tex = re.sub(r"[_^]\{\}", "", tex)
    tex = re.sub(r"\s+", " ", tex).strip()
    return ("$" + tex + "$") if tex else ""


# ---------------------------------------------------------------------------
# Statement HTML -> LaTeX
# ---------------------------------------------------------------------------

_HEADING_MAP = {
    "题目描述": "题目描述",
    "问题描述": "问题描述",
    "输入格式": "输入格式",
    "输出格式": "输出格式",
    "约束条件": "约束条件",
    "数据范围": "约束条件",
    "说明": "必要说明",
    "样例输入": "样例输入",
    "样例输出": "样例输出",
    "样例 1 输入": "样例输入",
    "样例一输入": "样例输入",
    "样例 1 输出": "样例输出",
    "样例1输入": "样例输入",
    "样例1输出": "样例输出",
    "样例输入 1": "样例输入",
    "样例输出 1": "样例输出",
    "输出": "样例输出",
    "提示": "提示",
    "本地评测说明": "__drop__",
}

_MATH_RE = re.compile(r"<math\b.*?</math>", re.S | re.I)
_PRE_RE = re.compile(r"<pre\b[^>]*>\s*<code\b[^>]*>(.*?)</code>\s*</pre>", re.S | re.I)
_IMG_RE = re.compile(r'<img\b[^>]*src=["\']([^"\']+)["\'][^>]*>', re.I)


def _clean_inline(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\r\n", "\n")
    return text


class _StmtParser(HTMLParser):
    """Collect linear tokens: ('text', s), ('start', tag, attrs), ('end', tag)."""

    def __init__(self, html_text):
        super().__init__(convert_charrefs=True)
        self.tokens = []
        self.feed(html_text)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("start", tag, dict(attrs)))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(("startend", tag, dict(attrs)))

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag))

    def handle_data(self, data):
        self.tokens.append(("text", data))


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "^": r"\^{}",
    "~": r"\textasciitilde{}",
}


def _escape_text(s):
    return "".join(_LATEX_ESCAPES.get(c, c) for c in s)


def render_statement_latex(html_text, image_dir=None):
    """Render the statement HTML to a LaTeX body (without document wrapper)."""
    if image_dir:
        os.makedirs(image_dir, exist_ok=True)

    sentinel_math = []
    sentinel_pre = []
    sentinel_img = []
    images = []

    def sub_math(m):
        idx = len(sentinel_math)
        sentinel_math.append(mathml_to_latex(m.group(0)))
        return "\x01M%d\x02" % idx

    def sub_pre(m):
        idx = len(sentinel_pre)
        # extract raw source
        raw = m.group(1)
        src = _clean_inline(raw)
        src = re.sub(r"\s+$", "", src)
        sentinel_pre.append(src)
        return "\x01P%d\x02" % idx

    def sub_img(m):
        idx = len(sentinel_img)
        src = m.group(1).strip()
        fname = os.path.basename(src.split("?")[0])
        if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".png")):
            fname = "fig%d%s" % (idx, os.path.splitext(fname)[1])
        images.append((src, fname))
        sentinel_img.append(fname)
        return "\x01I%d\x02" % idx

    html_text = _MATH_RE.sub(sub_math, html_text)
    # Strip the "本地评测说明" (local-evaluation note) — it is metadata, not
    # problem content. It appears as a paragraph, sometimes bold, sometimes an
    # <h4> heading.
    html_text = re.sub(r"<p>(?:(?!</p>).)*?本地评测说明.*?</p>", "", html_text, flags=re.S)
    html_text = re.sub(r"<p>(?:(?!</p>).)*?本地评测说明.*", "", html_text, flags=re.S)
    html_text = re.sub(r"<strong>\s*本地评测说明[^\n]*", "", html_text)
    html_text = re.sub(r"本地评测说明[^\n<]*", "", html_text)
    html_text = _PRE_RE.sub(sub_pre, html_text)
    html_text = _IMG_RE.sub(sub_img, html_text)

    parser = _StmtParser(html_text)

    blocks = []
    cur = []  # current inline parts

    i = 0
    toks = parser.tokens

    # We accumulate per-`li` and per-`p` text; on block end flush.
    pending_block = None  # 'p' | 'li' | 'h' | 'pre'
    list_stack = []

    def emit_inline(txt):
        cur.append(txt)

    def end_block():
        nonlocal pending_block, cur
        # flush whatever inline content accumulated in cur
        if cur:
            if cur[0] == "\x01li\x02":
                blocks.append(("li", "".join(cur[1:])))
            else:
                blocks.append(("p", "".join(cur)))
            cur = []
        pending_block = None

    while i < len(toks):
        tok = toks[i]
        kind = tok[0]
        if kind == "start":
            tag = tok[1]
            attrs = tok[2]
            if tag in ("p", "div"):
                end_block()
                pending_block = "p"
            elif tag in ("h3", "h4", "h5"):
                end_block()
                pending_block = "h"
                # heading content inline until </h>
                blocks.append(("h", "".join(cur)))
                cur[:] = []
                # gather heading text until end tag
                inner = []
                j = i + 1
                while j < len(toks) and not (toks[j][0] == "end" and toks[j][1] in ("h3", "h4", "h5")):
                    t = toks[j]
                    if t[0] == "text":
                        inner.append(t[1])
                    elif t[0] == "startend" and t[1] == "br":
                        inner.append(" ")
                    j += 1
                heading_text = "".join(inner)
                heading_text = re.sub(r"\s+", " ", heading_text).strip()
                # resolve
                norm = _HEADING_MAP.get(heading_text, heading_text)
                if norm == "__drop__":
                    blocks.pop()
                    # drop until next block (skip body under this heading)
                else:
                    blocks[-1] = ("h", norm)
                i = j  # skip to end tag
            elif tag == "ul":
                end_block()
                list_stack.append("itemize")
                blocks.append(("begin", "itemize"))
            elif tag == "ol":
                end_block()
                list_stack.append("enumerate")
                blocks.append(("begin", "enumerate"))
            elif tag == "li":
                end_block()
                pending_block = "li"
                cur = ["\x01li\x02"]
            elif tag in ("strong", "b"):
                cur.append(r"\textbf{")
            elif tag in ("em", "i"):
                cur.append(r"\textit{")
            elif tag == "code" and pending_block != "pre":
                cur.append(r"\texttt{")
            elif tag == "br":
                cur.append("\\\\\n")
            elif tag == "pre":

                end_block()
                pending_block = "pre"
                blocks.append(("pre", ""))
                cur = []
                # read until </pre> and collect raw text/sentinels
                j = i + 1
                inner = []
                while j < len(toks) and not (toks[j][0] == "end" and toks[j][1] == "pre"):
                    t = toks[j]
                    inner.append(t[1] if t[0] == "text" else "")
                    j += 1
                raw = "".join(inner)
                blocks[-1] = ("pre", raw)
                i = j
                cur = []
                pending_block = None
            elif tag == "img":
                continue
        elif kind == "startend":
            tag = tok[1]
            if tag == "br":
                cur.append("\\\\\n")
        elif kind == "end":
            tag = tok[1]
            if tag in ("p", "div"):
                end_block()
            elif tag in ("ul", "ol"):
                if list_stack:
                    list_stack.pop()
                blocks.append(("end", "itemize" if not list_stack else "itemize"))  # generic
            elif tag == "li":
                end_block()
            elif tag in ("strong", "b", "em", "i"):
                cur.append("}")
            elif tag == "code":
                cur.append("}")
        elif kind == "text":
            data = tok[1]
            if pending_block == "pre":
                pass  # pre raw captured separately
            else:
                if pending_block == "li" and cur and cur[0] == "\x01li\x02":
                    pass
                emit_inline(_apply_sentinels(data, sentinel_math, sentinel_pre, sentinel_img))
        i += 1

    # flush leftover
    end_block()

    # Build final body by walking blocks, handling itemize/enumerate nesting,
    # converting pre blocks to verbatim and dropping any dropped content.
    return _assemble(blocks, sentinel_math, sentinel_pre, sentinel_img, images)


def _apply_sentinels(text, math, pre, img):
    # text may contain sentinels; replace
    def rep_math(m):
        return math[int(m.group(1))]

    def rep_pre(m):
        # pre inside inline context -> verbatim inline
        return "\n\\begin{verbatim}\n%s\n\\end{verbatim}\n" % pre[int(m.group(1))]

    def rep_img(m):
        return _img_cmd(img[int(m.group(1))], int(m.group(1)))

    out = text
    out = re.sub(r"\x01M(\d+)\x02", rep_math, out)
    out = re.sub(r"\x01P(\d+)\x02", rep_pre, out)
    out = re.sub(r"\x01I(\d+)\x02", rep_img, out)
    return out


def _img_cmd(fname, idx):
    return "\n\\begin{center}\n\\includegraphics[width=0.7\\textwidth]{%s}\n\\end{center}\n" % fname


def _assemble(blocks, math, pre, img, images):
    out = []
    stack = []
    for blk in blocks:
        kind, val = blk
        if kind == "begin":
            stack.append(val)
            out.append("\\begin{%s}" % val)
        elif kind == "end":
            stack.append(val)
            out.append("\\end{%s}" % val)
        elif kind == "h":
            # keep standard heading names
            out.append("\\subsection*{%s}" % _escape_text(val))
        elif kind == "p":
            out.append(val.strip() + "\n\n" if val.strip() else "")
        elif kind == "li":
            out.append("  \\item " + val + "\n")
        elif kind == "pre":
            out.append("\\begin{verbatim}\n%s\n\\end{verbatim}\n" % val.replace("\u00a0", " "))
    body = "\n".join(x for x in out if x)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body


# ---------------------------------------------------------------------------
# Vector of helpers for sample extraction
# ---------------------------------------------------------------------------

_CODE_RE = re.compile(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>", re.S | re.I)


def _unescape_code(t: str) -> str:
    text = re.sub(r"<[^>]+>", "", t)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.rstrip()
    return text


def extract_samples(html_text):
    """Return list of (input_text, output_text) public samples."""
    parts = re.split(r"(<h[34][^>]*>.*?</h[34]>)", html_text, flags=re.S)
    seq = []
    for part in parts:
        if re.match(r"<h[34]", part):
            head = re.sub(r"<[^>]+>", "", part)
            head = re.sub(r"\s+", " ", head).strip()
            seq.append(("h", head))
        else:
            seq.append(("b", part))
    samples = []
    i = 0
    pending_in = None
    last_head = "other"
    while i < len(seq):
        kind, val = seq[i]
        if kind == "h":
            head = val
            if re.search(r"样例\s*\d*\s*输入", head) or head in ("样例输入",) or re.search(r"^\s*\d+\s*输入\s*$", head):
                last_head = "input"
            elif re.search(r"样例\s*\d*\s*输出", head) or head in ("样例输出", "输出") or re.search(r"^\s*\d+\s*输出\s*$", head):
                last_head = "output"
            else:
                last_head = "other"
            if last_head == "output":
                pass
        else:
            matches = _CODE_RE.findall(val)
            if last_head == "input" and matches:
                pending_in = _unescape_code(matches[-1])
            elif last_head == "output" and pending_in is not None and matches:
                out = _unescape_code(matches[-1])
                samples.append((pending_in, out))
                pending_in = None
            # if an input heading's body had no pre, clear pending on other heading
            if last_head == "other":
                pass
        i += 1
    return samples


if __name__ == "__main__":
    import json

    base = os.path.join(os.path.dirname(__file__), "..", "work")
    with open(os.path.join(base, "exercises.json")) as f:
        data = json.load(f)
    for e in data:
        print("###", e["exercise_number"], "|", e["title"])
        print(" ID:", slug_for_id(e["title"]))
        ss = extract_samples(e["problem_statement"] or "")
        for s in ss:
            print("  SAMPLE %r -> %r" % s)
        # quick statement render check
        body = render_statement_latex(e["problem_statement"] or "", image_dir="/tmp/_img")
        if body.strip():
            print("  RENDER (first 160):", (body[:160]).replace("\n", " "))
