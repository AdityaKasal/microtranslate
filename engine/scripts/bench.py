"""BLEU + chrF + throughput for the quantized model, with and without the
neutro layer. Also checks whether the FLORES reference is even a fair judge
of Latin American register."""
import pathlib, sys, time, re
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import sacrebleu
from engine import Engine
from neutro import to_neutro

ROOT = pathlib.Path(__file__).resolve().parents[1]
FL = ROOT / "data" / "flores200_dataset" / "devtest"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1012

src = FL.joinpath("eng_Latn.devtest").read_text().splitlines()[:N]
ref = FL.joinpath("spa_Latn.devtest").read_text().splitlines()[:N]
print(f"FLORES-200 devtest, en -> es, {len(src)} sentences\n")

CACHE = ROOT / "bench" / f"hyp_raw_{N}.txt"
chars = sum(len(s) for s in src)
if CACHE.exists():
    hyp = CACHE.read_text().splitlines()
    print(f"translate: (cached {CACHE.name})")
else:
    eng = Engine(threads=8)
    t0 = time.time(); hyp = eng.translate(src, beam_size=4); dt = time.time() - t0
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text("\n".join(hyp))
    print(f"translate: {dt:.1f}s  |  {len(src)/dt:.1f} sent/s  |  {chars/dt:,.0f} src chars/s")

t1 = time.time(); hyp_n = [to_neutro(h) for h in hyp]; dtn = time.time() - t1
print(f"neutro layer: {dtn*1000:.0f}ms total ({dtn/len(src)*1000:.3f}ms per sentence)\n")

for label, h in (("raw int8", hyp), ("int8 + neutro", hyp_n)):
    b = sacrebleu.corpus_bleu(h, [ref])
    c = sacrebleu.corpus_chrf(h, [ref])
    print(f"{label:16} BLEU {b.score:5.2f}   chrF2 {c.score:5.2f}")

changed = sum(1 for a, b in zip(hyp, hyp_n) if a != b)
print(f"\nneutro layer altered {changed}/{len(src)} outputs ({changed/len(src)*100:.1f}%)")

# Is the FLORES Spanish reference itself peninsular? If so BLEU cannot score
# Latin American register fairly, and the probe set is the real judge.
PEN = ["ordenador","móvil","zumo","patata","nevera","fontanero","gafas",
       "ascensor","billete","melocot","camarero","bañador","calcetines",
       "cerilla","aparca","conducir","portátil","coger","vosotros","vuestr"]
hits = {}
for w in PEN:
    n = sum(1 for r in ref if re.search(rf"(?<!\w){w}", r, re.I))
    if n: hits[w] = n
print(f"\npeninsular forms present in the FLORES *reference*: "
      f"{sum(hits.values())} occurrences across {len(hits)} word families")
for w, n in sorted(hits.items(), key=lambda x: -x[1]):
    print(f"   {w:12} {n}")
