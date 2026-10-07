"""Read the sample texts in data/texts/*.txt and turn them into glossed sentences.

A text file has these line types:
  @ the title
  % one line about the text
  > the sentence as tokens: a gloss key, then affix labels (water-PL-ACC)
  = the English translation of the sentence before it
  # a comment
"""

import lang

TEXTS = lang.ROOT / "data" / "texts"


def load(lex):
    texts = []
    for path in sorted(TEXTS.glob("*.txt")):
        text = {"id": path.stem, "title": "", "about": "", "sentences": []}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tag, rest = line[0], line[1:].strip()
            if tag == "@":
                text["title"] = rest
            elif tag == "%":
                text["about"] = rest
            elif tag == ">":
                text["sentences"].append({"tokens": rest, "english": "", "cols": lang.compose(lex, rest)})
            elif tag == "=":
                text["sentences"][-1]["english"] = rest
            else:
                raise ValueError(f"{path.name}: unknown line '{line}'")
        texts.append(text)
    return texts


def spelled(sentence):
    """The Oruhi sentence as one string, with its closing period."""
    return " ".join(c["form"] for c in sentence["cols"]) + "."
