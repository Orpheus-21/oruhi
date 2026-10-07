"""Oruhi: the language definition.

This file is the one source of truth for the sounds, the syllables, the
affixes, and the number system. The check, the font, and the site read it.
The words live in data/lexicon.tsv.
"""

import random
import re
from collections import namedtuple
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "data" / "lexicon.tsv"

# Sounds. The letter o is kept for holy words: a word has an o only if it is holy.
CONSONANTS = "ptkmnshr"
VOWELS = "aiuo"
ORDINARY = "aiu"
SYLLABLE = re.compile(r"[ptkmnshr]?[aiuo]")
FINALS = ["pi", "tu", "mu", "nu", "sa", "hi", "ra", "ru", "na"]  # a root ends in one of these

# Affixes: label -> (form, meaning). Every affix is a suffix.
AFFIX = {
    "PL": ("ka", "more than one"),
    "ACC": ("ni", "the thing that the verb acts on"),
    "GEN": ("si", "belonging to"),
    "DAT": ("ti", "to, for"),
    "LOC": ("pu", "at, in, on"),
    "ABL": ("su", "from, out of"),
    "INS": ("ku", "with, by means of"),
    "COM": ("mi", "together with"),
    "PAST": ("ta", "before now"),
    "FUT": ("pa", "after now"),
    "NEG": ("nahu", "not"),
    "IMP": ("ha", "a command"),
    "NMLZ": ("ki", "the act or the state of the verb"),
    "AGENT": ("ri", "the one who does the verb"),
    "HON": ("o", "honor, or address to the holy"),
}
CASES = ["ACC", "GEN", "DAT", "LOC", "ABL", "INS", "COM"]

# A word takes at most one affix from each slot, in slot order.
NOUN_SLOTS = [{"PL"}, set(CASES), {"HON"}]
VERB_SLOTS = [{"PAST", "FUT"}, {"NEG"}, {"IMP"}, {"HON"}]
DERIVE = {"NMLZ", "AGENT"}  # a verb or adjective plus one of these becomes a noun
SLOTS = {"n": NOUN_SLOTS, "pron": NOUN_SLOTS, "v": VERB_SLOTS, "adj": VERB_SLOTS}
POS = ["n", "pron", "v", "adj", "num", "adv", "part"]

DIGIT = ["zero", "one", "two", "three", "four", "five", "six", "seven"]  # the base is 8

Entry = namedtuple("Entry", "form pos gloss tags note")


# ---- sounds ----

def syllables(word):
    """Split a word into syllables, or return None if it does not tile."""
    w = word.lower().replace("-", "")
    out, i = [], 0
    while i < len(w):
        m = SYLLABLE.match(w, i)
        if not m:
            return None
        out.append(m.group())
        i = m.end()
    return out or None


def legal(word):
    """A word is open syllables. A bare vowel stands only first, or as the final -o."""
    syl = syllables(word)
    if not syl:
        return False
    last = len(syl) - 1
    return all(len(s) == 2 or k == 0 or (k == last and s == "o") for k, s in enumerate(syl))


def holy(word):
    return "o" in word.lower()


def show(form):
    """Romanize a form. Holy words start with a capital letter."""
    return form[:1].upper() + form[1:] if holy(form) else form


# ---- affix rules ----

def _walk(slots):
    for pick in product(*[[None] + sorted(s) for s in slots]):
        yield tuple(label for label in pick if label)


def chains(pos):
    """Every legal row of affix labels for a part of speech."""
    if pos in ("v", "adj"):
        yield from _walk(VERB_SLOTS)
        for d in sorted(DERIVE):
            for rest in _walk(NOUN_SLOTS):
                yield (d,) + rest
    elif pos in ("n", "pron"):
        yield from _walk(NOUN_SLOTS)
    else:
        yield ()


VALID = {pos: set(chains(pos)) for pos in POS}
_BY_LENGTH = sorted(((f, label) for label, (f, _) in AFFIX.items()), key=lambda x: -len(x[0]))


def analyses(lex, word):
    """Every (entry, labels) pair that spells the word. One pair means no doubt."""
    found = []

    def walk(stem, labels):
        for e in lex.by_form.get(stem, ()):
            if labels in VALID[e.pos]:
                found.append((e, labels))
        for f, label in _BY_LENGTH:
            if len(stem) > len(f) and stem.endswith(f):
                walk(stem[: -len(f)], (label,) + labels)

    walk(word.lower().replace("-", ""), ())
    return found


def compose_word(lex, token):
    """Turn a token such as 'water-PL-ACC' into the spelled word and its parts."""
    lemma, *labels = token.split("-")
    e = lex.by_gloss.get(lemma)
    if e is None:
        raise KeyError(f"no word has the gloss '{lemma}'")
    labels = tuple(labels)
    if labels not in VALID[e.pos]:
        raise ValueError(f"'{token}': the affixes {labels} are not legal for a {e.pos}")
    parts = [e.form] + [AFFIX[label][0] for label in labels]
    return "".join(parts), "-".join(parts)


def compose(lex, tokens):
    """Turn a sentence of tokens into Oruhi. Returns the columns for each word."""
    cols = []
    for token in tokens.split():
        if token == ".":
            continue
        lemma, *labels = token.split("-")
        form, seg = compose_word(lex, token)
        gloss = "-".join([lemma.replace("_", ".")] + list(labels))
        cols.append({"form": show(form), "seg": seg, "gloss": gloss})
    return cols


def gloss(lex, sentence):
    """Turn a sentence of Oruhi into columns of form, parts, and gloss."""
    cols = []
    for word in re.findall(r"[A-Za-z-]+", sentence):
        found = analyses(lex, word)
        if not found:
            cols.append({"form": word, "seg": "?", "gloss": "?", "count": 0})
            continue
        e, labels = found[0]
        parts = [e.form] + [AFFIX[label][0] for label in labels]
        cols.append({
            "form": show(word.lower()),
            "seg": "-".join(parts),
            "gloss": "-".join([e.gloss.replace("_", ".")] + list(labels)),
            "count": len(found),
        })
    return cols


# ---- numbers ----

def octal(n):
    return oct(n)[2:]


def say(lex, n):
    """Read a number digit by digit in base 8. Zero is always spoken."""
    return " ".join(show(lex.by_gloss[DIGIT[int(d)]].form) for d in octal(n))


def read(lex, text):
    value = {lex.by_gloss[g].form: i for i, g in enumerate(DIGIT)}
    n = 0
    for w in text.lower().split():
        n = n * 8 + value[w]
    return n


# ---- the lexicon ----

class Lexicon:
    def __init__(self, entries):
        self.entries = entries
        self.by_form, self.by_gloss = {}, {}
        for e in entries:
            if e.form:
                self.by_form.setdefault(e.form.lower(), []).append(e)
            self.by_gloss[e.gloss] = e


def load(path=LEXICON):
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            c = (line.split("\t") + [""] * 5)[:5]
            entries.append(Entry(*c))
    return Lexicon(entries)


def generate(entry, used):
    """Make a form for one word. The result depends only on the gloss, so it is stable."""
    tags = set(entry.tags.split())
    sacred = "H" in tags
    n = 2 if "f" in tags or entry.pos in ("pron", "part", "adv", "num") else 3
    cv = [c + v for c in CONSONANTS for v in ORDINARY]
    for attempt in range(20000):
        rng = random.Random(f"oruhi/{entry.gloss}/{attempt}")
        syl = [rng.choice(cv) for _ in range(n)]
        if rng.random() < 0.08:
            syl[0] = rng.choice(ORDINARY)
        syl[-1] = rng.choice(FINALS)
        if sacred:
            j = rng.randrange(n)
            syl[j] = "o" if j == 0 and rng.random() < 0.25 else (syl[j][:-1] + "o" if len(syl[j]) == 2 else "o")
        if any(a == b for a, b in zip(syl, syl[1:])):
            continue
        w = "".join(syl)
        if not legal(w) or w in used or (holy(w) != sacred):
            continue
        if ("S" in tags and "i" not in w) or ("L" in tags and "a" not in w) or ("D" in tags and "u" not in w):
            continue
        return w
    raise RuntimeError(f"no form found for '{entry.gloss}'")


def fill(path=LEXICON):
    """Fill every blank form in the lexicon file. A filled form never changes."""
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [(line.split("\t") + [""] * 5)[:5] if line.strip() and not line.startswith("#") else None for line in lines]
    used = {r[0] for r in rows if r and r[0]}
    made = 0
    for i, r in enumerate(rows):
        if r and not r[0]:
            r[0] = generate(Entry(*r), used)
            used.add(r[0])
            lines[i] = "\t".join(r)
            made += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return made
