"""Build refs_th.tex: Thai-version reference list in the style of the Thai example
(docs/paper/Example/[THAI]-67076012-Short Paper-1.pdf): numbered [n] in order of
first citation, APA-style entries (Author, I. (year). Title. Venue, pages. DOI / สืบค้นจาก URL).
Source of truth is docs/paper/references.bib; run after editing the Thai body.
Usage: python make_refs_th.py   (from this folder)
"""
import re
import os

here = os.path.dirname(os.path.abspath(__file__))
bib_path = os.path.join(here, "..", "..", "..", "references.bib")
bib = open(bib_path, encoding="utf-8").read()

entries = {}
for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", bib, re.S):
    kind, key, body = m.groups()
    fields = {}
    for fm in re.finditer(r"^\s*(\w+)\s*=\s*\{(.*)\}\s*,?\s*$", body, re.M):
        fields[fm.group(1)] = fm.group(2)
    fields["_kind"] = kind
    entries[key] = fields


def clean(s):
    s = re.sub(r"\\texttt\{((?:\\_|[^{}])*)\}", lambda m: "\x01" + m.group(1) + "\x02", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("--", "\u2013")
    s = s.replace("\x01", "\\texttt{").replace("\x02", "}")
    return s


def initials(first):
    parts = re.split(r"[\s]+", first.strip())
    out = []
    for p in parts:
        sub = p.split("-")
        out.append("-".join(x[0] + "." for x in sub if x))
    return " ".join(out)


def authors(a):
    a = clean_authors(a)
    return a


def clean_authors(a):
    names = [x.strip() for x in re.split(r"\s+and\s+", a)]
    out = []
    etal = False
    for n in names:
        if n == "others":
            etal = True
            continue
        n0 = n
        if n0.startswith("{"):
            out.append(clean(n0))
            continue
        last, first = [x.strip() for x in n0.split(",", 1)]
        out.append(last + ", " + initials(first))
    if etal or len(out) > 8:
        out = out[:6]
        return ", ".join(out) + ", และคณะ"
    if len(out) == 1:
        return out[0]
    if len(out) == 2:
        return out[0] + ", \\& " + out[1]
    return ", ".join(out[:-1]) + ", \\& " + out[-1]


def fmt(key):
    e = entries[key]
    au = clean_authors(e["author"])
    yr = e["year"]
    title = clean(e["title"])
    s = au + " (" + yr + "). " + title + ("" if title[-1] in "?." else ".")
    if "booktitle" in e:
        v = "\\textit{" + clean(e["booktitle"]) + "}"
        if "volume" in e:
            v += ", " + e["volume"]
            if "number" in e:
                v += "(" + e["number"] + ")"
        if "pages" in e:
            v += ", " + clean(e["pages"])
        s += " " + v + "."
    if "howpublished" in e:
        s += " " + clean(e["howpublished"]) + "."
    if "eprint" in e:
        s += " arXiv:" + e["eprint"] + "."
    if "note" in e:
        s += " " + clean(e["note"]) + ("" if e["note"].endswith(".") else ".")
    if "doi" in e:
        s += " doi:" + e["doi"].replace("_", r"\_")
    elif "url" in e:
        s += " สืบค้นจาก \\url{" + e["url"] + "}"
    return s


order = []
for fn in ["abstract_th.tex", "body_th.tex"]:
    t = open(os.path.join(here, fn), encoding="utf-8").read()
    for m in re.finditer(r"\\cite\{([^}]*)\}", t):
        for k in m.group(1).split(","):
            k = k.strip()
            if k not in order:
                order.append(k)
missing = [k for k in order if k not in entries]
assert not missing, missing
unused = [k for k in entries if k not in order]
print("not cited, omitted:", unused)

lines = ["\\begin{thebibliography}{99}", "\\raggedright\\small"]
for k in order:
    lines.append("\\bibitem{" + k + "} " + fmt(k))
lines.append("\\end{thebibliography}")
open(os.path.join(here, "refs_th.tex"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print(len(order), "entries")
