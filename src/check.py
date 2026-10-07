"""Check the whole language. Run: python3 src/check.py
The exit code is 1 if any check fails."""

import sys
import tempfile
from pathlib import Path

import lang
import script
import texts as Texts

failures = []


def ok(condition, message):
    if not condition:
        failures.append(message)


def check_lexicon(lex):
    forms, glosses = {}, {}
    for e in lex.entries:
        ok(e.form, f"'{e.gloss}' has no form")
        ok(e.pos in lang.POS, f"'{e.gloss}' has the unknown part of speech '{e.pos}'")
        ok(lang.legal(e.form), f"'{e.gloss}': the form '{e.form}' breaks the syllable rules")
        tags = e.tags.split()
        ok(("H" in tags) == lang.holy(e.form), f"'{e.gloss}': the o rule fails for '{e.form}'")
        ok("S" not in tags or "i" in e.form, f"'{e.gloss}' is tagged S but '{e.form}' has no i")
        ok("L" not in tags or "a" in e.form, f"'{e.gloss}' is tagged L but '{e.form}' has no a")
        ok("D" not in tags or "u" in e.form, f"'{e.gloss}' is tagged D but '{e.form}' has no u")
        ok(e.form not in forms, f"'{e.gloss}' and '{forms.get(e.form)}' share the form '{e.form}'")
        ok(e.gloss not in glosses, f"the gloss '{e.gloss}' is used twice")
        forms[e.form], glosses[e.gloss] = e.gloss, True
    ok(len(lex.entries) >= 500, f"the lexicon has {len(lex.entries)} words; the goal is 500")


def check_affixes():
    forms = [f for f, _ in lang.AFFIX.values()]
    ok(len(set(forms)) == len(forms), "two affixes share one form")
    for label, (f, _) in lang.AFFIX.items():
        ok(lang.legal(f), f"the affix {label} '{f}' breaks the syllable rules")
    for label in lang.DERIVE | {c for slot in lang.NOUN_SLOTS + lang.VERB_SLOTS for c in slot}:
        ok(label in lang.AFFIX, f"the slot label {label} has no affix")


def check_words_with_affixes(lex):
    """Every legal affix chain must spell a legal word that parses back to one analysis."""
    for e in lex.entries:
        for labels in lang.chains(e.pos):
            word = e.form + "".join(lang.AFFIX[label][0] for label in labels)
            ok(lang.legal(word), f"'{e.gloss}' with {labels} gives the illegal word '{word}'")
            found = lang.analyses(lex, word)
            ok(found == [(e, labels)], f"'{word}' ({e.gloss} {labels}) parses as {[(x.gloss, l) for x, l in found]}")


def check_numbers(lex):
    for n in range(4096):
        ok(lang.read(lex, lang.say(lex, n)) == n, f"the number {n} does not read back")
    ok(lang.say(lex, 0) == "Oru", "zero must be spoken as Oru")
    ok(lang.say(lex, 8).endswith("Oru"), "the number 8 must speak its zero")


def check_texts(lex):
    """Every sample sentence must compose, and must parse back to the same parts."""
    try:
        texts = Texts.load(lex)
    except (KeyError, ValueError) as err:
        ok(False, f"a text does not compose: {err}")
        return
    ok(texts, "no sample texts found")
    for t in texts:
        for s in t["sentences"]:
            where = f"{t['id']}: {s['tokens']}"
            ok(s["english"], f"{where}: no English translation")
            back = lang.gloss(lex, Texts.spelled(s))
            ok(len(back) == len(s["cols"]), f"{where}: the word count changes on the way back")
            for a, b in zip(s["cols"], back):
                ok((a["seg"], a["gloss"], b["count"]) == (b["seg"], b["gloss"], 1), f"{where}: '{a['form']}' does not parse back to one analysis")


def check_script(lex):
    """Every syllable in use needs a glyph, and no two glyphs may look the same."""
    words = [e.form for e in lex.entries] + [f for f, _ in lang.AFFIX.values()]
    for w in words:
        for syl in lang.syllables(w):
            ok(syl in script.GLYPHS, f"the syllable '{syl}' in '{w}' has no glyph")
    ok(len(script.GLYPHS) == len(lang.SYLLABLES) + 8 + 1, "the glyph count is wrong")
    ok(len(set(script.TICK.values())) == len(lang.CONSONANTS) == 8, "the 8 consonants need 8 different ring places")
    looks = {}
    for key, shapes in script.GLYPHS.items():
        ok(repr(shapes) not in looks, f"the glyphs '{key}' and '{looks.get(repr(shapes))}' look the same")
        looks[repr(shapes)] = key


def check_font():
    """Build the font and test that the ligatures exist. Needs fonttools; skipped without it."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("skipped the font check: fonttools is not installed")
        return
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.ttf"
        script.build_font(path)
        font = TTFont(path)
    ligatures = sum(len(v) for lk in font["GSUB"].table.LookupList.Lookup for st in lk.SubTable if hasattr(st, "ligatures") for v in st.ligatures.values())
    ok(ligatures == len(lang.CONSONANTS) * len(lang.VOWELS), f"the font has {ligatures} ligatures, not 32")
    ok(font["name"].getDebugName(1) == "Oruhi Ring", "the font family name is wrong")
    cmap = font.getBestCmap()
    ok(all(cmap.get(ord(d)) for d in "01234567"), "a digit has no glyph")


def main():
    lex = lang.load()
    check_lexicon(lex)
    check_affixes()
    check_words_with_affixes(lex)
    check_numbers(lex)
    check_texts(lex)
    check_script(lex)
    check_font()
    for f in failures[:40]:
        print("FAIL", f)
    print(f"{len(lex.entries)} words, {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
