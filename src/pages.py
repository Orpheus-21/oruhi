"""Build the generated parts of the website. Run: .venv/bin/python src/pages.py

Each page in docs/ holds markers: <!--gen:name args-->...<!--/gen:name-->.
This script fills the space between the two markers from the language data.
Run it again after any change to the data. The pages need no other build step.
"""

import contextlib
import io
import math
import re
from html import escape as e

import cli
import lang
import script
import texts as Texts

DOCS = lang.ROOT / "docs"
REPO = "https://github.com/Orpheus-21/oruhi"
PAGES = [
    ("index.html", "Home"), ("sounds.html", "Sounds"), ("script.html", "Script"), ("grammar.html", "Grammar"),
    ("numbers.html", "Numbers"), ("lexicon.html", "Lexicon"), ("texts.html", "Texts"), ("tools.html", "Tools"),
    ("about.html", "About"),
]
MARK = re.compile(r"<!--gen:(\w+)\b([^>]*?)-->(.*?)<!--/gen:\1-->", re.S)
PLACE = {90: "top", 45: "top right", 0: "right", -45: "bottom right", -90: "bottom", -135: "bottom left", 180: "left", 135: "top left"}
LEX = TEXTS = None


def ring(text, cls=""):
    return f'<span class="{("ring " + cls).strip()}" lang="x-oruhi">{e(text)}</span>'


def table(head, rows, cls=""):
    th = "".join(f'<th scope="col">{h}</th>' for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl"><table{f' class="{cls}"' if cls else ""}><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def ipa(word):
    syl = ["".join("ɾ" if ch == "r" else ch for ch in s) for s in lang.syllables(word)]
    syl[-2 if len(syl) > 1 else 0] = "ˈ" + syl[-2 if len(syl) > 1 else 0]
    return "[" + ".".join(syl) + "]"


def lab(gloss):
    return re.sub(r"(-?)\b([A-Z]{2,})\b", r'<span class="lab">\1\2</span>', e(gloss))  # the hyphen stays inside the label


# ---- generators: each takes the marker arguments and returns HTML ----

def g_count(a):
    words = len(LEX.entries)
    holy = sum(lang.holy(x.form) for x in LEX.entries)
    n = {"words": words, "holy": holy, "ordinary": words - holy, "syllables": len(lang.SYLLABLES), "glyphs": len(script.GLYPHS),
         "affixes": len(lang.AFFIX), "texts": len(TEXTS), "sentences": sum(len(t["sentences"]) for t in TEXTS)}
    return str(n[a])


def g_nav(a, page=""):
    items = "".join(f'<li><a href="{f}"{" aria-current=\"page\"" if f == page else ""}>{e(n)}</a></li>' for f, n in PAGES)
    return (f'<nav class="site" aria-label="Pages"><a class="brand" href="index.html">{ring("Oruhi")}<span class="sr">Oruhi</span></a>'
            f'<ul>{items}</ul></nav>')


def g_footer(a):
    return (f'<footer class="site"><p>Oruhi is a constructed language. The data, the tools, and this site are free software under the '
            f'GNU General Public License, version 3 or any later version.</p><p><a href="{REPO}">Source code on GitHub</a></p></footer>')


def g_affixes(a):
    nouns = {l for slot in lang.NOUN_SLOTS for l in slot}
    verbs = {l for slot in lang.VERB_SLOTS for l in slot}
    rows = []
    for label, (form, meaning) in lang.AFFIX.items():
        if label in lang.DERIVE:
            attach, slot = "verbs and adjectives. The result is a noun.", "before slot 1 of the noun"
        else:
            where = [n for n, s in (("nouns and pronouns", nouns), ("verbs and adjectives", verbs)) if label in s]
            attach = " and ".join(where)
            slot = "slot " + str(next(i + 1 for i, s in enumerate(lang.NOUN_SLOTS if label in nouns else lang.VERB_SLOTS) if label in s))
        rows.append([f'<code class="lab">{label}</code>', f"<code>-{form}</code>", ring(form), e(meaning), attach, slot])
    return table(["Label", "Form", "Ring", "Meaning", "Attaches to", "Place"], rows)


def g_templates(a):
    def row(slots):
        return " + ".join("(" + "|".join(sorted(s, key=lambda x: list(lang.AFFIX).index(x))) + ")" for s in slots)
    lines = [f"noun, pronoun   stem + {row(lang.NOUN_SLOTS)}",
             f"verb, adjective stem + {row(lang.VERB_SLOTS)}",
             f"made noun       stem + (NMLZ|AGENT) + {row(lang.NOUN_SLOTS)}"]
    return '<pre class="plain"><code>' + "\n".join(lines) + "</code></pre>"


def g_chart(a):
    head = ["Consonant", "Place on the ring"] + [f"{v}" for v in lang.VOWELS]
    rows = [["none", "no tick"] + [f'<span class="cell">{ring(v)}<code>{v}</code></span>' for v in lang.VOWELS]]
    for c in lang.CONSONANTS:
        rows.append([f"<code>{c}</code>", PLACE[script.TICK[c]]] + [f'<span class="cell">{ring(c + v)}<code>{c}{v}</code></span>' for v in lang.VOWELS])
    return table(head, rows, "chart")


def g_wheel(a):
    shapes = [script.shape_svg(("ring", 0, 0, script.R_OUT, script.R_IN))]
    labels = []
    for c, ang in script.TICK.items():
        t = math.radians(ang)
        shapes.append(script.shape_svg(("rect", 340 * math.cos(t), 340 * math.sin(t), 140, 64, ang)))
        labels.append(f'<text x="{560 * math.cos(t):.0f}" y="{-560 * math.sin(t):.0f}" text-anchor="middle" dominant-baseline="central">{c}</text>')
    return ('<svg class="wheel" viewBox="-760 -760 1520 1520" role="img" aria-label="A ring with eight ticks. The consonants p, t, k, m, n, s, h, r '
            'stand at the top, top right, right, bottom right, bottom, bottom left, left, and top left." fill="currentColor">'
            f'<g transform="scale(1 -1)">{"".join(shapes)}</g>{"".join(labels)}</svg>')


def g_digits(a):
    rows = []
    for d, key in enumerate(lang.DIGIT):
        form = lang.show(LEX.by_gloss[key].form)
        rows.append([ring(str(d), "big"), f"<code>{d}</code>", f"<code>{form}</code>", ring(form, "big"), e(key)])
    return table(["Numeral", "Digit", "Word", "Ring word", "Meaning"], rows)


def g_numbers(a):
    picks = [0, 1, 7, 8, 9, 15, 16, 24, 63, 64, 100, 205, 512, 1000, 4095]
    rows = [[f"<code>{n}</code>", f"<code>{lang.octal(n)}</code>", ring(lang.octal(n), "big"), f"<code>{lang.say(LEX, n)}</code>"] for n in picks]
    return table(["Decimal", "Base 8", "Ring numerals", "Spoken"], rows)


def g_pronouns(a):
    rows = []
    for x in LEX.entries:
        if x.pos == "pron":
            rows.append([f"<code>{lang.show(x.form)}</code>", ring(x.form), e(x.gloss.replace("_", " ")), e(x.note)])
    return table(["Form", "Ring", "Gloss", "Note"], rows)


def g_lexicon(a):
    rows = []
    for x in sorted(LEX.entries, key=lambda x: x.gloss):
        q = e(f"{x.gloss.replace('_', ' ')} {x.form}", quote=True)
        holy = ' class="holy"' if lang.holy(x.form) else ""
        rows.append(f'<tr data-pos="{x.pos}" data-q="{q}"><td>{ring(x.form)}</td><td><code{holy}>{lang.show(x.form)}</code></td>'
                    f'<td>{x.pos}</td><td>{e(x.gloss.replace("_", " "))}</td><td>{e(x.note)}</td></tr>')
    head = "".join(f'<th scope="col">{h}</th>' for h in ["Ring", "Form", "Class", "Gloss", "Note"])
    return f'<div class="tbl"><table id="lex" class="lex"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def g_sounds(a):
    picks = ["zero", "I", "you", "water", "void", "ring", "first_break", "great_empty", "sun", "river", "bread", "pilgrim"]
    rows = []
    for g in picks:
        form = LEX.by_gloss[g].form
        rows.append([f"<code>{lang.show(form)}</code>", ring(form), f"<code>{ipa(form)}</code>", str(len(lang.syllables(form))), e(g.replace("_", " "))])
    return table(["Form", "Ring", "Sound", "Syllables", "Gloss"], rows)


def g_tags(a):
    names = {"S": ("small things", "i"), "L": ("large things", "a"), "D": ("dark and deep things", "u")}
    rows = []
    for tag, (what, vowel) in names.items():
        words = [x for x in LEX.entries if tag in x.tags.split()]
        rows.append([f"<code>{tag}</code>", what, f"<code>{vowel}</code>", ", ".join(f"{e(x.gloss.replace('_', ' '))} <code>{x.form}</code>" for x in words)])
    return table(["Tag", "Meaning", "The word has", "Words"], rows)


def sentence(s):
    cols = "".join(f'<span class="w"><span class="f">{e(c["form"])}</span><span class="s">{e(c["seg"])}</span><span class="g">{lab(c["gloss"])}</span></span>' for c in s["cols"])
    return (f'<figure class="sent"><div class="ring line" lang="x-oruhi">{e(Texts.spelled(s))}</div><div class="gl">{cols}</div>'
            f'<figcaption>{e(s["english"])}</figcaption></figure>')


def text_by_id(i):
    return next(t for t in TEXTS if t["id"] == i)


def g_text(a):
    t = text_by_id(a.strip())
    return f'<p class="about">{e(t["about"])}</p>' + "".join(sentence(s) for s in t["sentences"])


def g_sentence(a):
    i, tokens = a.strip().split(" ", 1)
    return sentence(next(s for s in text_by_id(i)["sentences"] if s["tokens"] == tokens))


def spiral_text(i):
    return " ".join(Texts.spelled(s) for s in text_by_id(i)["sentences"])


def g_spiral(a):
    return script.spiral_svg(spiral_text(a.strip()), px=0, color=None).replace("<svg ", '<svg class="spiral" ', 1)


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli.main(list(argv))
    cmd = "python3 src/cli.py " + " ".join(f'"{x}"' if " " in x else x for x in argv)
    return f'<figure class="term"><figcaption><code>{e(cmd)}</code></figcaption><pre><code>{e(out.getvalue().rstrip())}</code></pre></figure>'


def g_cli(a):
    """The real output of one tool. The argument is the name of the tool."""
    myth = text_by_id("myth")["sentences"][0]
    return "".join({
        "lookup": [run("lookup", "water")],
        "compose": [run("compose", "I water-ACC drink-PAST-NEG")],
        "gloss": [run("gloss", Texts.spelled(myth).rstrip("."))],
        "number": [run("number", "205"), run("number", lang.say(LEX, 133))],
    }[a])


GENS = {n[2:]: f for n, f in globals().items() if n.startswith("g_")}


def fill(path):
    src = path.read_text(encoding="utf-8")

    def sub(m):
        name, arg = m.group(1), m.group(2).strip()
        body = GENS[name](arg, path.name) if name == "nav" else GENS[name](arg)
        return f"<!--gen:{name}{(' ' + arg) if arg else ''}-->{body}<!--/gen:{name}-->"

    out = MARK.sub(sub, src)
    if out != src:
        path.write_text(out, encoding="utf-8")


def build(font=True):
    global LEX, TEXTS
    LEX = lang.load()
    TEXTS = Texts.load(LEX)
    (DOCS / "img").mkdir(parents=True, exist_ok=True)
    (DOCS / "fonts").mkdir(parents=True, exist_ok=True)
    if font:
        script.build_font(DOCS / "fonts" / "oruhi-ring.ttf")
    (DOCS / "img" / "prayer-spiral.svg").write_text(script.spiral_svg(spiral_text("prayer"), px=0.05), encoding="utf-8")
    forms = [lang.show(LEX.by_gloss[g].form) for g in lang.DIGIT]
    (DOCS / "data.js").write_text("// Made by src/pages.py. Do not edit.\nconst DIGITS = " + str(forms).replace("'", '"') + ";\n", encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    for f, _ in PAGES:
        if (DOCS / f).exists():
            fill(DOCS / f)


if __name__ == "__main__":
    build()
