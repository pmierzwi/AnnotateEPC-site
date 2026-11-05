"""Citations in free text (comments): "Art. 84", "Article 54(3) EPC", "Rule 36(1)(a)",
"Art. 2(1) RFees", "art. 84 ust. 1 lit. a", "F-IV, 4.6", "Guidelines G-VII, 6", "T 305/87".

Standard library only: this module is also copied into the public site repository, where a
GitHub workflow links the citations in new comments (site_repo/link_comments.py).

A citation is linked only if the provision exists (`index`: node id -> page path of its unit);
anything else is left as it is. Text that is already a link, code or a URL is not touched, so
linking twice changes nothing.
"""

import re
from dataclasses import dataclass

DASH = "\\-\u2010\u2011\u2012\u2013\u2014"  # for use in [...]: hyphens, en/em dashes
_D = f"[{DASH}]"

_ART = r"(?:Articles?|Arts?\.?|Artikel|articles?|art\.|Art\.)"
_RULE = (r"(?:Rules?|R\.?(?=\s?\d)|Regeln?|r[èe]gles?|R[èe]gles?|[Zz]asad[a-ząęy]*"
         r"|[Rr]egu[łl][a-ząęy]*)")  # "R.", "R 88", "R51(1)"
_NUM = r"\d+[a-z]?"
# paragraphs/letters: "(3)(a)", "(1) (a)", PL "ust. 1 lit. a", DE "Abs. 1 Buchst. a"
_SUB = (r"(?:\s?\(\s?\d+[a-z]?\s?\))*(?:\s?\(\s?[a-z]\s?\))*"
        r"(?:\s+(?:ust\.|Abs\.)\s*\d+[a-z]?)?(?:\s+(?:lit\.|Buchst\.)\s*[a-z]\b)?")
_JOIN = r"(?:\s*,\s*|\s+(?:and|or|to|und|oder|bis|et|ou|à|i|lub|oraz|do)\s+|\s*" + _D + r"\s*)"
_INSTR = (r"(?:\s+(?P<instr>EPC|EP[ÜU]|CBE|KPE|RFees|GebO|RRT|IR)"
          r"(?P<y1973>\s*1973)?)?")
PROVISION = re.compile(
    rf"(?<![\w.])(?P<kind>{_ART}|{_RULE})\s*(?P<first>{_NUM}{_SUB})"
    rf"(?P<more>(?:{_JOIN}{_NUM}{_SUB}(?![\w/]|\.\d))*){_INSTR}(?![\w])")
_ITEM = re.compile(rf"(?P<num>{_NUM})(?P<sub>{_SUB})")
_PARTS = re.compile(r"\(\s?(\d+[a-z]?|[a-z])\s?\)|(?:ust\.|Abs\.)\s*(\d+[a-z]?)"
                    r"|(?:lit\.|Buchst\.)\s*([a-z])")

# Explicit instrument citations are parsed before the EPC shorthand. Keep their entire
# spans reserved even when a target is absent, so a missing PCT node never becomes EPC.
_EXT_NUM = r"\d+(?:bis|ter|quater|quinquies|sexies|septies|[a-z])?"
_EXT_SUB = r"(?:\.[A-Z]|[A-Z])?(?:\." + _EXT_NUM + r")?(?:\s*\(\w+\))*"
_EXT_ITEM = re.compile(rf"(?P<num>{_EXT_NUM})(?P<sub>{_EXT_SUB})")
EXTERNAL = re.compile(
    rf"(?<![\w.])(?P<kind>{_ART}|{_RULE})\s*(?P<first>{_EXT_NUM}{_EXT_SUB})"
    rf"(?P<more>(?:{_JOIN}{_EXT_NUM}{_EXT_SUB})*)\s+"
    r"(?:of\s+(?:the\s+)?)?(?P<act>Patent Cooperation Treaty|PCT-R|PCT|"
    r"Paris Convention|PC|PVÜ|UPR|UPCA|RFeesUPP|"
    r"(?:Regulation\s*\(EU\)\s*(?:No\.?\s*)?)(?:1257|1260)/2012)\b")


def _external_node(kind: str, act: str, num: str, sub: str) -> str:
    rule = re.match(r"(?:Rules?|R\.?|Regeln?|[Rr][èe]gles?)$", kind) is not None
    if act in ("PCT", "PCT-R", "Patent Cooperation Treaty"):
        work = "pctr" if rule or act == "PCT-R" else "pct"
    elif act in ("Paris Convention", "PC", "PVÜ"):
        work = "paris"
    elif "1257/2012" in act:
        work = "eu1257"
    elif "1260/2012" in act:
        work = "eu1260"
    else:
        work = {"UPR": "upr", "UPCA": "upca", "RFeesUPP": "rfeesupp"}[act]
    parts = re.findall(r"[A-Z]|\d+(?:bis|ter|quater)?|(?<=\()[a-z]+", sub)
    return "/".join([work, "r" if work in ("pctr", "upr") else "art", num, *parts])


# A provision of another instrument (not modelled yet): leave it unlinked.
OTHER_ACT = re.compile(
    r"(?:\.(?:\d+(?:bis|ter|quater)?|[A-Z]))*\s*(?:\(\w{1,3}\)\s*)*(?:of\s+(?:the\s+)?)?"
    r"(?:Patent Law Treaty|Patent Cooperation Treaty"
    r"|Paris Convention|PLT|PCT|TRIPS|Strasbourg Convention|Budapest Treaty|UPCA?|PVÜ|PCT-?R"
    r"|eIDAS|(?:\w+\s+)?(?:Regulation|Directive)|UPR|RPBA|RPEBA)\b")
GUIDELINES = re.compile(
    rf"(?<![\w{DASH}])(?:(?:GL|Guidelines|Richtlinien|Directives|Wytyczne)\s+)?"
    rf"(?P<part>[A-H]){_D}(?P<chapter>[IVX]+)(?![\w{DASH}])"
    rf"(?:,?\s+(?P<section>\d+(?:\.\d+)*)(?![\d.]\d)"
    # end of a range or a second section: "3–6", "7.1 to 7.4", "3 and 4"
    rf"(?:(?P<sep>\s*{_D}\s*|\s+(?:to|and|bis|und|à|et|do|i)\s+)"
    rf"(?P<end>\d+(?:\.\d+)*)(?![\d.]\d|\w))?)?")
DECISION = re.compile(r"(?<![\w/])(?P<board>[GTJRWD])\s?(?P<num>\d{1,4})/(?P<year>\d{2})(?![\w/])")

# Spans that must not be changed: code, existing links/images, autolinks, URLs, HTML tags.
_PROTECTED = re.compile(
    r"```.*?```|`[^`\n]*`|!?\[[^\]]*\]\([^)]*\)|<https?://[^>]*>|https?://\S+|<[^>\n]+>",
    re.S)


@dataclass
class Cite:
    start: int
    end: int
    node: str


def _work(kind: str, instr: str | None, y1973: str | None, default_1973: bool) -> str:
    rule = re.match(r"(?:Rules?|R\.?|Regeln?|r[èe]gles?|R[èe]gles?|[Zz]asad[a-ząęy]*"
                    r"|[Rr]egu[łl][a-ząęy]*)$", kind) is not None
    old = bool(y1973) or (instr is None and default_1973)
    if instr in ("RFees", "GebO", "RRT"):
        base = "rfees"
    elif rule or instr == "IR":
        base = "ir"
    else:
        base = "epc"
    return base + ("1973" if old else "")


def _node(work: str, num: str, sub: str) -> str:
    seg = "r" if work.startswith("ir") else "art"
    parts = [next(g for g in m.groups() if g) for m in _PARTS.finditer(sub)]
    return "/".join([work, seg, num, *parts])


def find(text: str, index: dict[str, str], default_1973: bool = False) -> list[Cite]:
    """Citations of existing provisions in `text` (positions of the linkable text)."""
    out: list[Cite] = []
    external_spans = []
    for m in EXTERNAL.finditer(text):
        external_spans.append((m.start(), m.end()))
        for item, offset, start, end in [
            (_EXT_ITEM.fullmatch(m["first"]), 0, m.start(),
             m.end() if not m["more"] else m.end("first")),
            *((item, m.start("more"), None, None)
              for item in _EXT_ITEM.finditer(m["more"])),
        ]:
            node = _external_node(m["kind"], m["act"], item["num"], item["sub"])
            if node in index:
                out.append(Cite(start if start is not None else offset + item.start(),
                                end if end is not None else offset + item.end(), node))
    for m in PROVISION.finditer(text):
        if any(a <= m.start() < b for a, b in external_spans):
            continue
        if not m["instr"] and OTHER_ACT.match(text, m.end()):
            continue  # "Article 12 of the Patent Law Treaty", "Rule 13 PCT": not the EPC
        if re.match(r"\.\d", text[m.end():m.end() + 2]):
            continue  # "Rule 80.2": numbered like the PCT Regulations, not an EPC Rule
        work = _work(m["kind"], m["instr"], m["y1973"], default_1973)
        first = _ITEM.match(m["first"])
        node = _node(work, first["num"], first["sub"])
        prev = node
        # The first citation spans the word "Art." and the instrument if the list has one item.
        end = m.end() if not m["more"] else m.end("first")
        if node in index:
            out.append(Cite(m.start(), end, node))
        for item in _ITEM.finditer(m["more"] or ""):
            s, e = m.start("more") + item.start(), m.start("more") + item.end()
            node = _node(work, item["num"], item["sub"])
            if node != prev and node in index:
                out.append(Cite(s, e, node))
            prev = node
    for m in GUIDELINES.finditer(text):
        unit = f"gl/{m['part'].lower()}/{m['chapter'].lower()}"
        node = unit + ("/" + m["section"].replace(".", "/") if m["section"] else "")
        end = m.end("section") if m["end"] else m.end()
        if node in index:
            out.append(Cite(m.start(), end, node))
        if m["end"] and (last := f"{unit}/{m['end'].replace('.', '/')}") in index:
            out.append(Cite(m.start("end"), m.end("end"), last))
    for m in DECISION.finditer(text):
        out.append(Cite(m.start(), m.end(), f"case/{m['board']}-{int(m['num']):04d}-{m['year']}"))
    out.sort(key=lambda c: c.start)
    kept: list[Cite] = []
    for c in out:  # no overlaps
        if not kept or c.start >= kept[-1].end:
            kept.append(c)
    return kept


def anchor(node_id: str) -> str:
    return "n-" + re.sub(r"[^A-Za-z0-9]+", "-", node_id)


def url(node: str, index: dict[str, str], site: str) -> str:
    if node.startswith("case/"):
        b, n, y = node[5:].split("-")
        return f"{CASE_SEARCH}{b}+{n}%2F{y}"
    page = index[node]
    work, _, rest = node.partition("/")
    is_unit = page == f"{work}/{rest.replace('/', '-')}.html"  # same rule as site.page_path
    return f"{site}{page}" + ("" if is_unit else f"#{anchor(node)}")


CASE_SEARCH = "https://www.epo.org/en/results?q=&tab=boa&decision_case_number="


def unlink(text: str, site: str) -> str:
    """Removes the links this module makes (to the site and to the EPO case-law search), so
    that linking again uses the current parser and page structure."""
    ours = re.compile(r"\[([^\]]+)\]\((?:" + re.escape(site) + "|" + re.escape(CASE_SEARCH)
                      + r")[^)\s]*\)")
    return ours.sub(r"\1", text)


def link_markdown(text: str, index: dict[str, str], site: str,
                  default_1973: bool = False) -> tuple[str, int]:
    """Markdown with each citation turned into a link to the site; returns (text, count).
    Links made earlier by this function are made again (see `unlink`)."""
    text = unlink(text, site)
    out, pos, n = [], 0, 0
    spans = [(m.start(), m.end()) for m in _PROTECTED.finditer(text)] + [(len(text), len(text))]
    for a, b in spans:
        chunk = text[pos:a]
        cpos = 0
        for c in find(chunk, index, default_1973):
            label = chunk[c.start:c.end]
            out.append(chunk[cpos:c.start] + f"[{label}]({url(c.node, index, site)})")
            cpos, n = c.end, n + 1
        out.append(chunk[cpos:] + text[a:b])
        pos = b
    return "".join(out), n


def link_model(text: str, nodes) -> tuple[str, int]:
    """Plain text with citations turned into model links "[Article 122](epc/art/122)" (for
    importers of documents that cite provisions without links of their own)."""
    out, pos, n = [], 0, 0
    index = dict.fromkeys(nodes, "")
    for c in find(text, index):
        out.append(text[pos:c.start] + f"[{text[c.start:c.end]}]({c.node})")
        pos, n = c.end, n + 1
    out.append(text[pos:])
    return "".join(out), n
