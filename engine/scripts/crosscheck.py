#!/usr/bin/env python3
"""Assert the JavaScript register layer matches the Python one exactly.

The browser build reimplements neutro.py in JS. The two must never diverge, so
this runs both over the same corpus (every FLORES hypothesis plus the whole
regression set) and requires byte-identical output.

    python scripts/crosscheck.py
"""
import ast, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from neutro import to_neutro


def corpus():
    out = []
    for f in ("bench/hyp_raw_1012.txt", "bench/hyp_small_1012.txt"):
        p = ROOT / f
        if p.exists():
            out += p.read_text().splitlines()
    probes = ROOT / "data" / "register_probes.tsv"
    if probes.exists():
        out += [l.split("\t")[0] for l in probes.read_text().splitlines()[1:]]
    # the false-positive suite, read without executing its sys.exit
    tree = ast.parse((ROOT / "scripts" / "test_safety.py").read_text())
    out += next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and n.targets[0].id == "MUST_NOT_CHANGE")
    out += [
        "Comed la tarta y bebed el zumo.", "¿Dónde aparcasteis vuestros coches?",
        "Venid todos aquí.", "Mi portátil es muy ligero.",
        "Los ordenadores nuevos están en la mesa.", "Compré unas gafas oscuras.",
        "Sacad los calcetines de la nevera.", "El camarero cogió el billete.",
        "Francia es el séptimo país.", "Viajaron a París.", "Tengo sed.",
        "La ciudad y la libertad.", "Un coche bomba.", "Esto conduce a algo.",
    ]
    return out


def main():
    data = corpus()
    tmp = ROOT / "bench" / "_crosscheck_in.json"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    try:
        r = subprocess.run(["node", str(ROOT / "scripts" / "crosscheck.mjs"), str(tmp)],
                           capture_output=True, text=True)
    finally:
        tmp.unlink(missing_ok=True)
    if r.returncode:
        print("node failed:\n" + r.stderr[:2000])
        return 1
    js, py = json.loads(r.stdout), [to_neutro(s) for s in data]
    diff = [(c, a, b) for c, a, b in zip(data, py, js) if a != b]
    for c, a, b in diff[:10]:
        print(f"\nIN  {c}\nPY  {a}\nJS  {b}")
    print(f"{len(data)-len(diff)}/{len(data)} identical"
          + ("" if not diff else f"   >>> {len(diff)} MISMATCHES"))
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
