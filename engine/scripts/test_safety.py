"""False-positive regression tests: input that must pass through untouched."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from neutro import to_neutro

MUST_NOT_CHANGE = [
    "La ciudad es muy grande.",
    "Dime la verdad, por favor.",
    "La universidad defiende la libertad y la igualdad.",
    "Mi edad no importa.",
    "Viajamos a Madrid en diciembre.",
    "La amistad y la bondad son virtudes.",
    "Voy a recoger a los niños.",
    "Tienes que escoger uno.",
    "Nos acogieron con cariño.",
    "El piso estaba muy sucio.",          # piso = floor, deliberately excluded
    "Subimos al tercer piso.",
    "La mitad de la humanidad.",
    "Hay mucha claridad hoy.",
    "El personal de seguridad llegó.",
    "Protegen la propiedad privada.",
    "Es una oportunidad de verdad.",
    "La capacidad del auto es buena.",
    "Trabaja en publicidad.",
    # --- regressions found by benchmarking on FLORES, not by hand-written cases
    "Francia es el séptimo país de la Unión Europea.",   # -ís rule ate "país"
    "Viajaron de regreso a París en un carruaje.",       # ...and "París"
    "El anís es una especia aromática.",
    "siempre que la estación base tenga radios de doble banda",  # 3sg subjunctive
    "Espero que tenga un buen día.",
    "Tengo mucha sed después de correr.",               # "sed" = thirst, not a verb
    "Mi papá y mi mamá llegaron.",
    "Necesito mi licencia de conducir.",                # fixed LatAm collocation
    "Un coche bomba estalló en el centro.",             # fixed collocation
    "El accidente conduce a una investigación.",        # conducir = "lead to"
    "Eso conduce a mejores resultados.",
    "Aprendió a conducir el año pasado.",               # now deliberately unchanged
]

fails = []
for s in MUST_NOT_CHANGE:
    out = to_neutro(s)
    if out != s:
        fails.append((s, out))

for s, out in fails:
    print(f"FAIL  {s}\n  ->  {out}")
print(f"\n{len(MUST_NOT_CHANGE)-len(fails)}/{len(MUST_NOT_CHANGE)} passed through unchanged")
sys.exit(1 if fails else 0)
