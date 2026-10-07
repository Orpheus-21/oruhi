# Oruhi

Oruhi is a constructed language for a fictional people who worship the number zero.

The site is at https://orpheus-21.github.io/oruhi/

## What it does

The project holds the full description of the language and the tools that make and check it.

- The sounds: 8 consonants and 4 vowels, with open syllables only.
- The ring script: one glyph for each of the 36 syllables, 8 numeral glyphs, and a font that draws them.
- The grammar: suffixes only, with the verb last.
- A number system in base 8.
- A lexicon of 528 words.
- Sample texts: a myth, a prayer, a market dialogue, and one example for each grammar rule.
- Python tools that look up words, write and read sentences, convert numbers, and draw the script.
- A check script that tests all of the above.
- A website in `docs/` that shows the language.

## Requirements

- Python 3.12 or newer. The tools use only the standard library.
- `fonttools`, only to build the font and the site.
- A web browser, to read the site.

## Install

1. Clone the repository.

   ```
   git clone https://github.com/Orpheus-21/oruhi.git
   cd oruhi
   ```

2. Create a virtual environment for the font build.

   ```
   python3 -m venv .venv
   ```

3. Install `fonttools` in the environment.

   ```
   .venv/bin/pip install fonttools
   ```

Step 2 and step 3 are optional. Skip them if you only want the language tools and the check.

## Usage

Run all checks. The exit code is 1 if a check fails.

```
.venv/bin/python src/check.py
```

Without `fonttools`, the check skips the font test and prints a message.

The tools are subcommands of `src/cli.py`.

| Command | What it does |
|---|---|
| `lookup WORD` | Find a word by its form or by its English gloss. |
| `compose "TOKENS"` | Write Oruhi from tokens such as `"I water-ACC drink-PAST-NEG"`. |
| `gloss "SENTENCE"` | Show the parts and the gloss of an Oruhi sentence. |
| `number VALUE` | Show a number in base 10, base 8, and Oruhi. The value is digits or Oruhi words in quotes. |
| `ring "TEXT"` | Write the text in the ring script as an SVG image. Add `--spiral` for a spiral and `-o FILE` for a file. |
| `font` | Build the font file `docs/fonts/oruhi-ring.ttf`. This command needs `fonttools`. |
| `gen` | Fill blank forms in `data/lexicon.tsv`. A filled form never changes. |

Example:

```
python3 src/cli.py compose "I water-ACC drink-PAST-NEG"
```

```
minu  kanani     karatanahu
minu  kana-ni    kara-ta-nahu
I     water-ACC  drink-PAST-NEG
minu kanani karatanahu.
```

Build the font and fill the generated parts of the site:

```
.venv/bin/python src/pages.py
```

Open `docs/index.html` in a browser to read the result.

## Configuration

The language has no settings file. The data files are the settings.

| File | Content |
|---|---|
| `data/lexicon.tsv` | One word on each line: form, part of speech, gloss, tags, note. |
| `data/texts/*.txt` | The sample texts. A `>` line holds tokens. An `=` line holds the translation. |
| `src/lang.py` | The sounds, the affixes, the affix order, and the number system. |
| `src/script.py` | The glyph shapes and the font build. |

The tags in the lexicon are `f` for a short two syllable word, `H` for a holy word, and `S`, `L`, `D` for a word with the vowel `i`, `a`, or `u`.

## How it works

`src/lang.py` is the single source of truth. It defines the syllable rules, the 15 affixes, and the slots that order them. It also holds the parser, the composer, the number reader, and the word generator.

The parser reads a word from the right. It removes one affix at a time until the rest is a root in the lexicon. The affix tables must also fit the part of speech of the root.

`generate` makes a form for each word that has no form. The result depends only on the gloss. For this reason, adding a word never changes the forms of other words.

`src/script.py` holds each glyph as a list of shapes. The same list makes the SVG output and the TrueType font. The font has a `liga` feature that turns Latin spelling into ring glyphs.

`src/check.py` tests the following:

- Every word follows the syllable rules, and only holy words contain `o`.
- No two words share a form or a gloss.
- Every word with every legal row of affixes gives a legal word with exactly one reading.
- Every number from 0 to 4095 reads back to itself.
- Every sample sentence composes and parses back to the same parts.
- Every syllable has a glyph, and no two glyphs look the same.
- The font builds and holds all 32 ligatures.

`src/pages.py` fills the generated parts of the pages in `docs/`. Each page holds markers such as `<!--gen:lexicon-->`. The script replaces the text between a pair of markers. The pages need no other build step.

## License

The project is free software under the GNU General Public License, version 3 or any later version. The full text is in the file `LICENSE`.
