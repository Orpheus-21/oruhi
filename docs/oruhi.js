// Small helpers for the Oruhi site. The ring script itself needs no script: the font draws it.
(() => {
  const $ = (id) => document.getElementById(id);

  // Same rule as lang.legal: open syllables. A bare vowel stands first, or as the final o.
  const legal = (w) => {
    const s = w.match(/[ptkmnshr]?[aiuo]/g);
    if (!s || s.join("") !== w) return false;
    return s.every((x, i) => x.length === 2 || i === 0 || (i === s.length - 1 && x === "o"));
  };

  // The lexicon search box and the class filter.
  const q = $("lex-q"), pos = $("lex-pos"), count = $("lex-count");
  if (q && pos) {
    const rows = [...document.querySelectorAll("#lex tbody tr")];
    const run = () => {
      const text = q.value.trim().toLowerCase(), cls = pos.value;
      let shown = 0;
      rows.forEach((r) => {
        const hit = (!text || r.dataset.q.toLowerCase().includes(text)) && (!cls || r.dataset.pos === cls);
        r.hidden = !hit;
        shown += hit;
      });
      count.textContent = `${shown} of ${rows.length} words`;
    };
    q.addEventListener("input", run);
    pos.addEventListener("change", run);
    run();
  }

  // The ring script box: the font draws the text. This code only checks the spelling.
  const tin = $("try-in"), tout = $("try-out"), tmsg = $("try-msg");
  if (tin) {
    const run = () => {
      const text = tin.value;
      tout.textContent = text;
      const bad = text.toLowerCase().split(/[^a-z]+/).filter((w) => w && !legal(w));
      tmsg.textContent = bad.length ? `These words break the syllable rules: ${bad.join(", ")}. The font leaves out the letters that it cannot place.` : "";
      tmsg.className = bad.length ? "bad" : "";
    };
    tin.addEventListener("input", run);
    run();
  }

  // The number box: base 10 in, base 8 and Oruhi out.
  const nin = $("num-in"), nout = $("num-out"), nbase = $("num-base"), nsay = $("num-say"), nmsg = $("num-msg");
  if (nin && typeof DIGITS !== "undefined") {
    const run = () => {
      const v = nin.value.trim();
      if (!/^\d{1,9}$/.test(v)) {
        nmsg.textContent = v ? "Type a whole number from 0 to 999999999." : "";
        nout.textContent = nbase.textContent = nsay.textContent = "";
        return;
      }
      nmsg.textContent = "";
      const oct = Number(v).toString(8);
      nout.textContent = oct;
      nbase.textContent = oct;
      nsay.textContent = [...oct].map((d) => DIGITS[Number(d)]).join(" ");
    };
    nin.addEventListener("input", run);
    run();
  }
})();
