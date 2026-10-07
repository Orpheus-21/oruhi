"""The Oruhi ring script: glyph shapes, SVG output, and the font build.

A glyph is a list of shapes on a plane with y up and the center of the ring at (0, 0):
  ("ring", cx, cy, r_out, r_in)    a ring
  ("rect", cx, cy, w, h, angle)    a rectangle turned by `angle` degrees, counterclockwise
  ("dot", cx, cy, r)               a filled dot
  ("poly", [(x, y), ...])          a filled polygon, with its points in clockwise order

How to read a glyph:
  The ring is the zero. A syllable is a ring.
  A tick outside the ring names the consonant. The ring has 8 places for 8 consonants.
  A mark inside the ring names the vowel: a triangle for a, a stem for i, a bowl for u.
  The vowel o has no mark: the ring stays empty.
  A numeral is a ring on a base line, with dots inside. Only numerals have a base line.
"""

import math
import re

import lang

R_OUT, R_IN = 300, 240
ADV = 900          # width of one glyph, in font units (1000 units to the em)
BASE = 350         # height of the ring center above the font baseline
TICK = dict(zip(lang.CONSONANTS, [90, 45, 0, -45, -90, -135, 180, 135]))  # angle of each consonant
HEX = [(120 * math.cos(math.radians(90 + 60 * k)), 120 * math.sin(math.radians(90 + 60 * k))) for k in range(6)]
TRIANGLE = [(0, 130), (120, -90), (-120, -90)]
BOWL = [(-150, 20), (150, 20)] + [(150 * math.cos(math.radians(p)), 20 + 150 * math.sin(math.radians(p))) for p in range(-10, -180, -10)]
DOTS = [
    [],
    [(0, 0)],
    [(-80, 0), (80, 0)],
    [(0, 90), (-85, -60), (85, -60)],
    [(-80, -80), (80, -80), (80, 80), (-80, 80)],
    [(-80, -80), (80, -80), (80, 80), (-80, 80), (0, 0)],
    [(x, y) for x in (-100, 0, 100) for y in (-70, 70)],
    [(0, 0)] + HEX,
]


def glyphs():
    """Map each key to its shapes. Keys: a syllable ('ka', 'a'), a digit ('0' to '7'), or '.'."""
    g = {}
    for s in lang.SYLLABLES:
        c, v = (s[0], s[1]) if len(s) == 2 else ("", s)
        shapes = [("ring", 0, 0, R_OUT, R_IN)]
        if c:
            a = math.radians(TICK[c])
            shapes.append(("rect", 340 * math.cos(a), 340 * math.sin(a), 140, 64, TICK[c]))
        if v == "a":
            shapes.append(("poly", TRIANGLE))
        elif v == "i":
            shapes.append(("rect", 0, 0, 56, 260, 0))
        elif v == "u":
            shapes.append(("poly", BOWL))
        g[s] = shapes
    for d, dots in enumerate(DOTS):
        g[str(d)] = [("ring", 0, 0, R_OUT, R_IN), ("rect", 0, -370, 460, 56, 0)] + [("dot", x, y, 34) for x, y in dots]
    g["."] = [("ring", 0, -230, 70, 36)]
    return g


GLYPHS = glyphs()
TOKEN = re.compile(r"[A-Za-z-]+|[0-7]+|\.|\s+")


def keys(text):
    """Turn text into glyph keys. None marks the gap between two words."""
    out = []
    for m in TOKEN.finditer(text):
        t = m.group()
        if t.isspace():
            out.append(None)
        elif t == ".":
            out.append(".")
        elif t[0].isdigit():
            out.extend(t)
        else:
            syl = lang.syllables(t)
            if syl is None:
                raise ValueError(f"'{t}' is not a legal Oruhi word")
            out.extend(syl)
    return out


# ---- SVG ----

def shape_svg(s):
    if s[0] == "ring":
        _, cx, cy, ro, ri = s
        return f'<circle cx="{cx:g}" cy="{cy:g}" r="{(ro + ri) / 2:g}" fill="none" stroke="currentColor" stroke-width="{ro - ri:g}"/>'
    if s[0] == "rect":
        _, cx, cy, w, h, a = s
        return f'<rect x="{-w / 2:g}" y="{-h / 2:g}" width="{w:g}" height="{h:g}" transform="translate({cx:.1f} {cy:.1f}) rotate({a:g})"/>'
    if s[0] == "poly":
        return '<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in s[1]) + '"/>'
    _, cx, cy, r = s
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:g}"/>'


def _glyph(key, x, y, rot=0.0, scale=1.0):
    body = "".join(shape_svg(s) for s in GLYPHS[key])
    return f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.2f}) scale({scale:g} {-scale:g})">{body}</g>'


def _svg(w, h, body, px, color, label):
    size = f' width="{w * px:.0f}" height="{h * px:.0f}"' if px else ""
    style = f' style="color:{color}"' if color else ""   # no color: the page sets it
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}"{size} role="img" '
            f'aria-label="{label}" fill="currentColor"{style}>{body}</svg>\n')


def row_svg(text, per_line=24, px=0.06, color="#2a1d12"):
    """Write the text as rows of glyphs, left to right."""
    x, line, items = 0.0, 0, []
    for k in keys(text):
        if k is None:
            x += ADV * 0.5
            continue
        if x + ADV > per_line * ADV:
            x, line = 0.0, line + 1
        items.append(_glyph(k, x + ADV / 2, 500 + line * 1000))
        x += ADV
    width = (per_line * ADV) if line else x
    return _svg(width, 1000 + line * 1000, "".join(items), px, color, text)


def spiral_svg(text, px=0.05, color="#2a1d12", start=700, pitch=1000):
    """Write the text as a spiral. The first glyph is at the center. The spiral turns clockwise."""
    b = pitch / (2 * math.pi)
    th, items = 0.0, []

    def step(ds):
        nonlocal th
        r = start + b * th
        th += ds / math.hypot(r, b)

    for k in keys(text):
        if k is None:
            step(ADV * 0.55)
            continue
        r = start + b * th
        items.append((k, r * math.cos(th), r * math.sin(th), math.degrees(th) + 90))
        step(ADV * 0.98)
    reach = start + b * th + 700
    body = "".join(_glyph(k, x + reach, y + reach, rot) for k, x, y, rot in items)
    return _svg(2 * reach, 2 * reach, body, px, color, text)


# ---- the font ----

def build_font(path):
    """Write a TrueType font. Latin text in Oruhi spelling turns into ring glyphs (the `liga` feature)."""
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from fontTools.fontBuilder import FontBuilder
    from fontTools.misc.timeTools import epoch_diff
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    letters = lang.CONSONANTS + lang.VOWELS
    syl = sorted(k for k in GLYPHS if k.isalpha())
    names = [".notdef", "space", "hyphen", "period"] + [f"x_{c}" for c in letters] + [f"syl_{k}" for k in syl] + [f"num_{d}" for d in range(8)]

    def circle(pen, cx, cy, r, clockwise, n=16):
        big = r / math.cos(math.pi / n)   # off-curve points on a larger circle give a round contour
        sign = -1 if clockwise else 1
        pen.qCurveTo(*[(round(cx + big * math.cos(sign * 2 * math.pi * k / n)), round(cy + big * math.sin(sign * 2 * math.pi * k / n))) for k in range(n)], None)
        pen.closePath()

    def draw(shapes):
        pen = TTGlyphPen(None)
        ox, oy = ADV / 2, BASE
        for s in shapes:
            if s[0] == "ring":
                _, cx, cy, ro, ri = s
                circle(pen, ox + cx, oy + cy, ro, True)
                circle(pen, ox + cx, oy + cy, ri, False)
            elif s[0] == "rect":
                _, cx, cy, w, h, a = s
                t = math.radians(a)
                corners = [(-w / 2, h / 2), (w / 2, h / 2), (w / 2, -h / 2), (-w / 2, -h / 2)]  # clockwise
                pts = [(round(ox + cx + px * math.cos(t) - py * math.sin(t)), round(oy + cy + px * math.sin(t) + py * math.cos(t))) for px, py in corners]
                pen.moveTo(pts[0])
                for p in pts[1:]:
                    pen.lineTo(p)
                pen.closePath()
            elif s[0] == "poly":
                pts = [(round(ox + x), round(oy + y)) for x, y in s[1]]
                pen.moveTo(pts[0])
                for p in pts[1:]:
                    pen.lineTo(p)
                pen.closePath()
            else:
                _, cx, cy, r = s
                circle(pen, ox + cx, oy + cy, r, True)
        return pen.glyph()

    glyph = {n: TTGlyphPen(None).glyph() for n in names}
    advance = {n: 0 for n in names}
    advance[".notdef"], advance["space"] = 500, 450
    for k in syl:
        glyph[f"syl_{k}"], advance[f"syl_{k}"] = draw(GLYPHS[k]), ADV
    for d in range(8):
        glyph[f"num_{d}"], advance[f"num_{d}"] = draw(GLYPHS[str(d)]), ADV
    glyph["period"], advance["period"] = draw(GLYPHS["."]), 400

    cmap = {0x20: "space", 0x2D: "hyphen", 0x2E: "period"}
    cmap.update({0x30 + d: f"num_{d}" for d in range(8)})
    for c in letters:
        cmap[ord(c)] = cmap[ord(c.upper())] = f"x_{c}"
    cmap.update({0xE000 + i: f"syl_{k}" for i, k in enumerate(syl)})

    cv = "\n".join(f"  sub x_{k[0]} x_{k[1]} by syl_{k};" for k in syl if len(k) == 2)
    bare = "\n".join(f"  sub x_{k} by syl_{k};" for k in syl if len(k) == 1)
    fea = (f"languagesystem DFLT dflt;\nlanguagesystem latn dflt;\n"
           f"lookup cv {{\n{cv}\n}} cv;\nlookup bare {{\n{bare}\n}} bare;\n"
           f"feature liga {{\n  lookup cv;\n  lookup bare;\n}} liga;\n")

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyph)
    table = fb.font["glyf"]
    fb.setupHorizontalMetrics({n: (advance[n], getattr(table[n], "xMin", 0)) for n in names})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({
        "familyName": "Oruhi Ring", "styleName": "Regular", "uniqueFontIdentifier": "OruhiRing-Regular",
        "fullName": "Oruhi Ring", "psName": "OruhiRing-Regular", "version": "Version 1.000",
        "copyright": "Copyright 2026 Orpheus-21",
        "licenseDescription": "GNU General Public License, version 3 or any later version",
        "licenseInfoURL": "https://www.gnu.org/licenses/gpl-3.0.html",
    })
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, fea)
    fixed = 1791331200 - epoch_diff  # a fixed date, so every build gives the same file
    fb.font["head"].created = fb.font["head"].modified = fixed
    fb.font.recalcTimestamp = False
    fb.save(path)
