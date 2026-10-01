"""Measure how often the raw model picks peninsular forms over neutral LatAm."""
import csv, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from engine import Engine

ROOT = pathlib.Path(__file__).resolve().parents[1]

def hit(pattern, text):
    for alt in pattern.split("|"):
        if re.search(rf"(?<!\w){re.escape(alt.strip())}(?!\w)", text, re.I):
            return alt.strip()
    return None

def main(post=None):
    rows = list(csv.DictReader(open(ROOT/"data"/"register_probes.tsv"), delimiter="\t"))
    eng = Engine()
    outs = eng.translate([r["english"] for r in rows])
    if post:
        outs = [post(o) for o in outs]
    bad = good = neither = 0
    print(f"{'':2} {'EN':<40} {'ES':<52} verdict")
    print("-"*118)
    for r, es in zip(rows, outs):
        p, n = hit(r["peninsular"], es), hit(r["neutral"], es)
        if p and not n: v, bad = f"PENINSULAR ({p})", bad+1
        elif n and not p: v, good = "ok", good+1
        elif p and n: v, bad = f"MIXED ({p})", bad+1
        else: v, neither = "—", neither+1
        mark = " " if v=="ok" else "!"
        print(f"{mark}  {r['english'][:39]:<40} {es[:51]:<52} {v}")
    tot = len(rows)
    print("-"*118)
    print(f"neutral LatAm: {good}/{tot}   peninsular/mixed: {bad}/{tot}   unmatched: {neither}/{tot}")
    return good, bad, neither

if __name__ == "__main__":
    main()
