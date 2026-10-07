"""Oruhi tools. Run: python3 src/cli.py --help"""

import argparse
import sys

import lang


def table(cols):
    """Print columns as aligned lines: the form, the parts, the gloss."""
    for key in ("form", "seg", "gloss"):
        print("  ".join(c[key].ljust(max(len(c["form"]), len(c["seg"]), len(c["gloss"]))) for c in cols).rstrip())


def cmd_gen(lex, args):
    print(f"filled {lang.fill()} forms")


def cmd_lookup(lex, args):
    q = args.query.lower()
    hits = [e for e in lex.entries if e.gloss == q or e.form == q]
    if not hits:
        hits = [e for e in lex.entries if q in e.gloss]
    for e in hits:
        print(f"{lang.show(e.form):12} {e.pos:5} {e.gloss}  {e.note}".rstrip())
    if not hits:
        found = lang.analyses(lex, q)
        for e, labels in found:
            print(f"{lang.show(q)} = {lang.show(e.form)} ({e.pos}, {e.gloss}) + {'-'.join(labels) or 'no affix'}")
        if not found:
            sys.exit(f"no word matches '{args.query}'")


def cmd_gloss(lex, args):
    cols = lang.gloss(lex, args.sentence)
    table(cols)
    for c in cols:
        if c["count"] != 1:
            print(f"note: '{c['form']}' has {c['count']} analyses", file=sys.stderr)


def cmd_compose(lex, args):
    cols = lang.compose(lex, args.tokens)
    table(cols)
    print(" ".join(c["form"] for c in cols) + ".")


def cmd_number(lex, args):
    n = int(args.value) if args.value.isdigit() else lang.read(lex, args.value)
    print(f"decimal {n}")
    print(f"base 8  {lang.octal(n)}")
    print(f"Oruhi   {lang.say(lex, n)}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="cli.py", description="Tools for the Oruhi language.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gen", help="fill blank forms in data/lexicon.tsv").set_defaults(run=cmd_gen)
    s = sub.add_parser("lookup", help="find a word by form or by English gloss")
    s.add_argument("query")
    s.set_defaults(run=cmd_lookup)
    s = sub.add_parser("gloss", help="show the parts and the gloss of an Oruhi sentence")
    s.add_argument("sentence")
    s.set_defaults(run=cmd_gloss)
    s = sub.add_parser("compose", help="write Oruhi from tokens such as 'water-ACC drink-PAST'")
    s.add_argument("tokens")
    s.set_defaults(run=cmd_compose)
    s = sub.add_parser("number", help="show a number in base 10, base 8, and Oruhi")
    s.add_argument("value", help="a decimal number, or Oruhi digit words in quotes")
    s.set_defaults(run=cmd_number)
    args = p.parse_args(argv)
    args.run(lang.load(), args)


if __name__ == "__main__":
    main()
