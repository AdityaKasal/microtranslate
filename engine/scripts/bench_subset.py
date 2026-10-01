"""Is the small BLEU drop from the neutro layer real quality loss, or an
artifact of the FLORES reference using European Spanish?

Split the test set by whether the *reference* contains a peninsular form and
score each half separately.
"""
import pathlib, sys, re
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import sacrebleu
from neutro import to_neutro

ROOT = pathlib.Path(__file__).resolve().parents[1]
FL = ROOT / "data" / "flores200_dataset" / "devtest"
N = 1012
src = FL.joinpath("eng_Latn.devtest").read_text().splitlines()[:N]
ref = FL.joinpath("spa_Latn.devtest").read_text().splitlines()[:N]
hyp = (ROOT / "bench" / f"hyp_raw_{N}.txt").read_text().splitlines()
hyp_n = [to_neutro(h) for h in hyp]

PEN = r"(?<!\w)(ordenador|móvil|zumo|patata|nevera|fontanero|gafas|ascensor|" \
      r"billete|melocot|camarero|bañador|calcetines|cerilla|aparca|conducir|" \
      r"portátil|coger|vosotros|vuestr)"
clean = [i for i, r in enumerate(ref) if not re.search(PEN, r, re.I)]
dirty = [i for i, r in enumerate(ref) if re.search(PEN, r, re.I)]

def score(idx, label):
    r = [[ref[i] for i in idx]]
    a = sacrebleu.corpus_bleu([hyp[i] for i in idx], r).score
    b = sacrebleu.corpus_bleu([hyp_n[i] for i in idx], r).score
    d = b - a
    print(f"{label:38} n={len(idx):4}   raw {a:5.2f}   +neutro {b:5.2f}   "
          f"delta {d:+.2f}")
    return d

print("BLEU split by whether the REFERENCE itself uses European Spanish\n")
score(range(N),  "all sentences")
score(clean,     "reference has NO peninsular form")
score(dirty,     "reference HAS a peninsular form")
print()
chg = [i for i in range(N) if hyp[i] != hyp_n[i]]
chg_clean = [i for i in chg if i in set(clean)]
score(chg,       "only sentences the layer changed")
score(chg_clean, "  ...of those, clean references only")
