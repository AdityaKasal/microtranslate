# The español neutro layer

The base model produces **mixed** Spanish. Measured on 19 probes targeting
words that differ between Spain and Latin America, 15 came out European:
`ordenador`, `aparcamos el coche`, `patatas`, `nevera`, `fontanero`, `gafas`,
`ascensor`, `billete`, `melocotones`, `camarero`, `calcetines`, `portátil`,
`coger`. Meanwhile `jugo`, `papas`, `computadora`, `celular`, `pastel`,
`fósforo` and `traje de baño` already came out correctly.

Vosotros was a much smaller problem than expected — only 2 of 8 probes failed,
because the model already prefers `ustedes` and third-person plural. Measuring
first is what kept the morphology work proportionate.

## Three passes

1. **vosotros → ustedes.** Pronoun, possessive (`vuestro` → `su`), irregular
   verb forms (`tenéis` → `tienen`), and regular inflection by suffix
   (`-asteis` → `-aron`, `-abais` → `-aban`). Imperatives get a guarded suffix
   rule, below.
2. **Verb stems.** `aparcar` → `estacionar` across every inflection, generated
   by conjugating both verbs and zipping the forms, with Spanish spelling
   shifts applied (`aparqué` → `estacioné`). `coger` → `tomar` via explicit
   table: `coger` is vulgar across most of Latin America, so this one is not
   optional.
3. **Nouns, with agreement repair.** The delicate pass. Many substitutions
   flip grammatical gender, which drags the determiner and any agreeing
   adjective: `el ordenador` → `la computadora`, `los ordenadores nuevos` →
   `las computadoras nuevas`, `unas gafas oscuras` → `unos lentes oscuros`,
   `Mi portátil es muy ligero` → `Mi laptop es muy ligera` (predicative
   agreement through a copula). Where gender does *not* change, the determiner
   is left strictly alone.

## Deliberately excluded

Correctness beat coverage in four places, each found by benchmarking on real
text rather than by hand-written examples:

- **`conducir` → `manejar`: removed.** `conducir a X` also means *to lead to
  X*, where `manejar` is plainly wrong — `lo que conduce a una investigación`
  must not become `lo que maneja a`. `conducir` is standard across Latin
  America anyway (`licencia de conducir`), so the register gain did not
  justify breaking meaning.
- **`piso` → `departamento`: removed.** `piso` also means *floor/storey*
  (`el tercer piso`).
- **`acera`, `piscina`: left alone.** These are already the neutral
  pan-regional forms. A naive Spain→Mexico mapping would have wrongly pushed
  them to `banqueta` and `alberca`.
- **Region-specific forms avoided.** The target is *neutro*, not any one
  country, so `auto` over `carro`/`coche`, `autobús` over `camión`/`colectivo`,
  and no `pollera`/`birome`/`pileta`.

## Why imperatives need a guard, not a suffix rule

`-ad` → `-en` looks like a clean rule until it eats `ciudad`, `verdad`,
`edad`, `libertad`. The guard exploits the fact that nearly every Spanish
`-ad` noun is a `-dad`/`-tad` abstraction, leaving a short closed stoplist for
the rest. `-ed` and `-id` need their own stoplists — most importantly
**`usted`**, which an unguarded rule turns into `ustan`.

Stem-changing imperatives (`cerrad` → `cierren`, `volved` → `vuelvan`,
`seguid` → `sigan`) are listed explicitly and applied first; the suffix rule
only catches the regular tail (`sacad` → `saquen`, with `c` → `qu` applied).

Verified: 53/53 nouns with these endings pass through untouched, 22/22 regular
imperatives convert correctly.

## Bugs that only real data found

Hand-written examples passed while these were all broken. Each is now a
regression test in `scripts/test_safety.py`.

| Bug | Cause |
|---|---|
| `país` → `paen`, `París` → `Paren` | a generic `-ís` → `-en` verb rule |
| `tenga` → `tengan` | a 3rd-person *singular* subjunctive wrongly listed as a vosotros form |
| `sed` → `sean` | `sed` is the noun *thirst* |
| `id` → `vayan` | matched `ID` in technical text |
| `conduce al desarrollo` → `maneja al desarrollo` | the "lead to" sense of `conducir` |
| `la auto`, `La plomero`, `una boleto` | determiner map applied when gender did not flip |
| crash on `laptop es ligero` | optional regex group was `None` whenever the intensifier was absent |

## Known limits

- Adjective agreement is repaired for an adjective directly after the noun and
  for one across a simple copula. A distant or coordinated adjective
  (`la computadora, vieja y lenta`) is not reached.
- `os` → `les`/`los` is not attempted; choosing between dative and accusative
  needs parsing, not regex.
- The lexicon is 23 noun families. It is deliberately high-precision rather
  than broad — adding entries is cheap, and `data/lexicon.json` is the only
  file to touch.
- English ambiguity is the model's problem, not the layer's: *glasses* came
  back once as `copas` (drinking glasses) instead of `lentes`.
