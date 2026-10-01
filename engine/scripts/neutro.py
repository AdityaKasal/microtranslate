"""Rewrite European Spanish into neutral Latin American Spanish (español neutro).

Three passes, applied in order:
  1. vosotros -> ustedes  (morphological: pronoun, possessive, verb inflection)
  2. verb stem swaps      (aparcar -> estacionar, conducir -> manejar, coger -> tomar)
  3. noun swaps           (with determiner + adjective gender repair)

Pass 3 is the delicate one: many substitutions flip grammatical gender
(el ordenador -> la computadora), which drags the determiner and any
agreeing adjective with it.
"""
from __future__ import annotations
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEX = json.loads((ROOT / "data" / "lexicon.json").read_text())

# ---------------------------------------------------------------- determiners
_DET_M2F = {
    "el": "la", "los": "las", "un": "una", "unos": "unas",
    "del": "de la", "al": "a la",
    "este": "esta", "estos": "estas", "ese": "esa", "esos": "esas",
    "aquel": "aquella", "aquellos": "aquellas",
    "otro": "otra", "otros": "otras", "todo": "toda", "todos": "todas",
    "mucho": "mucha", "muchos": "muchas", "poco": "poca", "pocos": "pocas",
    "nuestro": "nuestra", "nuestros": "nuestras",
    "algún": "alguna", "ningún": "ninguna", "cuánto": "cuánta",
    "cuántos": "cuántas", "varios": "varias", "mismo": "misma",
    "mismos": "mismas",
}
_DET_F2M = {v: k for k, v in _DET_M2F.items()}
_DET_F2M.update({"de la": "del", "a la": "al"})

# Words that must never be mistaken for an agreeing adjective.
_NOT_ADJ = {
    "de", "del", "la", "el", "los", "las", "que", "y", "o", "en", "con", "por",
    "para", "a", "al", "no", "se", "lo", "su", "sus", "mi", "mis", "tu", "tus",
    "como", "pero", "si", "cuando", "donde", "desde", "hasta", "sobre", "entre",
    "sin", "tras", "ya", "muy", "más", "menos", "todo", "todos", "esto", "eso",
}
_COPULA = r"(?:es|era|está|estaba|fue|será|sería|parece|parecía|resulta|" \
          r"son|eran|están|estaban|fueron|serán|parecen|quedó|quedaron)"


def _match_case(src: str, tgt: str) -> str:
    if src[:1].isupper():
        return tgt[:1].upper() + tgt[1:]
    return tgt


def _flip_word(word: str, to: str) -> str:
    """Re-gender an adjective: to='f' turns -o/-os into -a/-as, and vice versa."""
    if to == "f":
        if word.endswith("os"): return word[:-2] + "as"
        if word.endswith("o"):  return word[:-1] + "a"
    else:
        if word.endswith("as"): return word[:-2] + "os"
        if word.endswith("a"):  return word[:-1] + "o"
    return word


def _repair_agreement(text: str, noun: str, to_gender: str) -> str:
    """Fix an adjective agreeing with `noun`, attributive or predicative."""
    g = to_gender
    # attributive: "la computadora nuevo" -> "nueva"
    def attr(m):
        adj = m.group(2)
        if adj.lower() in _NOT_ADJ or adj[:1].isupper():
            return m.group(0)
        return m.group(1) + _flip_word(adj, g)
    text = re.sub(rf"({re.escape(noun)}\s+)(\w+)", attr, text, flags=re.I)
    # predicative: "Mi laptop es muy ligero" -> "ligera"
    def pred(m):
        adj = m.group(3)
        if adj.lower() in _NOT_ADJ or adj[:1].isupper():
            return m.group(0)
        return m.group(1) + (m.group(2) or "") + _flip_word(adj, g)
    text = re.sub(
        rf"({re.escape(noun)}\s+{_COPULA}\s+)((?:muy|bastante|tan|poco|más|menos)\s+)?(\w+)",
        pred, text, flags=re.I)
    return text


# -------------------------------------------------------------- noun rewriting
# Fixed collocations that are standard in Latin America as they stand and must
# survive the noun pass untouched.
_PROTECTED = [
    "coche bomba", "coches bomba", "coche cama", "licencia de conducir",
    "permiso de conducir", "coche fúnebre",
]


def _rewrite_nouns(text: str) -> str:
    saved = {}
    for i, phrase in enumerate(_PROTECTED):
        tok = f"\x00{i}\x00"
        pat = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.I)
        def keep(m, tok=tok, saved=saved):
            saved[tok] = m.group(0)
            return tok
        text = pat.sub(keep, text)
    for e in LEX["entries"]:
        srcs, tgts = e["src"], e["tgt"]
        flip = e["src_g"] != e["tgt_g"]
        detmap = _DET_M2F if e["src_g"] == "m" else _DET_F2M
        for i, s in enumerate(srcs):
            t = tgts[i] if i < len(tgts) else tgts[-1]
            if flip:
                # Gender changes, so any determiner in front must change too.
                det_alt = "|".join(sorted(map(re.escape, detmap), key=len, reverse=True))
                pat = rf"(?<!\w)({det_alt})(\s+){re.escape(s)}(?!\w)"
                def with_det(m, t=t, detmap=detmap):
                    det = detmap.get(m.group(1).lower(), m.group(1))
                    return _match_case(m.group(1), det) + m.group(2) + t
                new = re.sub(pat, with_det, text, flags=re.I)
            else:
                # Same gender: leave the determiner alone.
                new = text
            new = re.sub(rf"(?<!\w){re.escape(s)}(?!\w)",
                         lambda m, t=t: _match_case(m.group(0), t), new, flags=re.I)
            if new != text and flip:
                new = _repair_agreement(new, t, e["tgt_g"])
            text = new
    for tok, original in saved.items():
        text = text.replace(tok, original)
    return text


# -------------------------------------------------------------- verb rewriting
_AR_ENDINGS = [
    "ar", "ando", "ado", "ada", "ados", "adas",
    "o", "as", "a", "amos", "áis", "an",
    "aba", "abas", "ábamos", "abais", "aban",
    "é", "aste", "ó", "asteis", "aron",
    "aré", "arás", "ará", "aremos", "aréis", "arán",
    "aría", "arías", "aríamos", "aríais", "arían",
    "e", "es", "emos", "éis", "en",
    "ara", "aras", "áramos", "arais", "aran",
    "ase", "ases", "ásemos", "aseis", "asen",
    "ad",
]

def _ortho(stem: str, ending: str) -> str:
    """Spanish spelling shifts before a front vowel: c->qu, g->gu, z->c."""
    if ending and ending[0] in "eé":
        if stem.endswith("c"): return stem[:-1] + "qu" + ending
        if stem.endswith("g"): return stem[:-1] + "gu" + ending
        if stem.endswith("z"): return stem[:-1] + "c" + ending
    return stem + ending


def _ar_pairs(src_inf: str, tgt_inf: str) -> list[tuple[str, str]]:
    ss, ts = src_inf[:-2], tgt_inf[:-2]
    pairs = [(_ortho(ss, e), _ortho(ts, e)) for e in _AR_ENDINGS]
    return sorted(pairs, key=lambda p: len(p[0]), reverse=True)


# conducir is irregular; manejar is a plain -ar verb.
_CONDUCIR = {
    "conducir": "manejar", "conduciendo": "manejando", "conducido": "manejado",
    "conduzco": "manejo", "conduces": "manejas", "conduce": "maneja",
    "conducimos": "manejamos", "conducís": "manejan", "conducen": "manejan",
    "conducía": "manejaba", "conducías": "manejabas",
    "conducíamos": "manejábamos", "conducían": "manejaban",
    "conduje": "manejé", "condujiste": "manejaste", "condujo": "manejó",
    "condujimos": "manejamos", "condujeron": "manejaron",
    "conduciré": "manejaré", "conducirá": "manejará",
    "conducirán": "manejarán", "conduciría": "manejaría",
    "conduzca": "maneje", "conduzcan": "manejen", "conduzcas": "manejes",
}
# coger is vulgar across most of Latin America: always rewrite.
_COGER = {
    "coger": "tomar", "cogiendo": "tomando", "cogido": "tomado",
    "cojo": "tomo", "coges": "tomas", "coge": "toma", "cogemos": "tomamos",
    "cogéis": "toman", "cogen": "toman",
    "cogía": "tomaba", "cogías": "tomabas", "cogíamos": "tomábamos",
    "cogían": "tomaban",
    "cogí": "tomé", "cogiste": "tomaste", "cogió": "tomó",
    "cogimos": "tomamos", "cogisteis": "tomaron", "cogieron": "tomaron",
    "cogeré": "tomaré", "cogerá": "tomará", "cogerán": "tomarán",
    "coja": "tome", "cojas": "tomes", "cojan": "tomen", "coged": "tomen",
}


def _rewrite_verbs(text: str) -> str:
    table: list[tuple[str, str]] = []
    for src, tgt in LEX["verbs"].items():
        if src.startswith("_"):
            continue
        if src == "conducir":
            table += list(_CONDUCIR.items())
        elif src.endswith("ar") and tgt.endswith("ar"):
            table += _ar_pairs(src, tgt)
    table += list(_COGER.items())
    for s, t in sorted(table, key=lambda p: len(p[0]), reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(s)}(?!\w)",
                      lambda m, t=t: _match_case(m.group(0), t), text, flags=re.I)
    return text


# ------------------------------------------------------- vosotros -> ustedes
_VOS_IRREG = {
    "sois": "son", "tenéis": "tienen", "habéis": "han", "estáis": "están",
    "vais": "van", "veis": "ven", "dais": "dan", "sabéis": "saben",
    "queréis": "quieren", "podéis": "pueden", "hacéis": "hacen",
    "decís": "dicen", "venís": "vienen", "oís": "oyen",
    "vivís": "viven", "salís": "salen", "escribís": "escriben",
    "recibís": "reciben", "subís": "suben", "abrís": "abren",
    "seguís": "siguen", "partís": "parten", "sufrís": "sufren",
    "seréis": "serán", "iréis": "irán", "tendréis": "tendrán",
    "venid": "vengan", "tened": "tengan", "haced": "hagan", "id": "vayan",
    "poned": "pongan", "decid": "digan", "salid": "salgan",
    "oíd": "oigan", "sabed": "sepan", "volved": "vuelvan",
    }
# Regular vosotros imperatives are listed explicitly rather than matched by
# suffix: -ad collides with very common nouns (ciudad, verdad, edad, amistad),
# and several of these verbs are stem-changing anyway (cerrad -> cierren).
_VOS_IMPERATIVE = {
    "comed": "coman", "bebed": "beban", "hablad": "hablen",
    "escuchad": "escuchen", "mirad": "miren", "esperad": "esperen",
    "entrad": "entren", "pasad": "pasen", "callad": "callen",
    "ayudad": "ayuden", "tomad": "tomen", "dejad": "dejen",
    "llevad": "lleven", "traed": "traigan", "leed": "lean",
    "abrid": "abran", "cerrad": "cierren", "seguid": "sigan",
    "escribid": "escriban", "cantad": "canten", "orad": "oren",
    "rezad": "recen", "perdonad": "perdonen", "recordad": "recuerden",
    "pensad": "piensen", "buscad": "busquen", "llamad": "llamen",
    "contad": "cuenten", "subid": "suban", "bajad": "bajen",
    "comprad": "compren", "trabajad": "trabajen", "descansad": "descansen",
    "empezad": "empiecen", "terminad": "terminen", "parad": "paren",
    "quedad": "queden", "preparad": "preparen", "recibid": "reciban",
    "estad": "estén", "alabad": "alaben", "mirad": "miren",
    "vivid": "vivan", "servid": "sirvan", "dormid": "duerman",
    "pedid": "pidan", "sentid": "sientan", "medid": "midan",
    "repetid": "repitan", "vestid": "vistan", "elegid": "elijan",
    "corregid": "corrijan", "partid": "partan", "unid": "unan",
    "sentaos": "siéntense", "levantaos": "levántense",
    "acercaos": "acérquense", "arrodillaos": "arrodíllense",
    "poneos": "pónganse", "callaos": "cállense",
}

# Regular vosotros imperatives, caught by suffix with a guard.
#   -ad -> -en   (hablad -> hablen, sacad -> saquen)
#   -ed -> -an   (comed  -> coman)
#   -id -> -an   (vivid  -> vivan)
# The guard matters: Spanish is full of nouns with these endings. Nearly every
# -ad noun is a -dad/-tad abstraction (ciudad, verdad, libertad), and the -ed
# and -id nouns form a short closed list -- notably "usted", which an unguarded
# rule would turn into "ustan". Stem-changing verbs (cerrad -> cierren) are
# handled by _VOS_IMPERATIVE above, which is applied first and wins.
_TAD_NOUNS = {
    "libertad", "voluntad", "amistad", "facultad", "lealtad", "dificultad",
    "mitad", "potestad", "majestad", "tempestad", "heredad",
}
_ED_NOUNS = {"sed", "red", "pared", "huésped", "césped", "usted", "merced",
             "sed", "ved"}
_ID_NOUNS = {"madrid", "vid", "ardid", "david", "cid", "adid"}


def _regular_imperative(word: str) -> str | None:
    w = word.lower()
    if w.endswith("ad"):
        if w.endswith("dad") or w in _TAD_NOUNS:
            return None
        return _ortho(word[:-2], "en")
    if w.endswith("ed"):
        if w in _ED_NOUNS:
            return None
        return _ortho(word[:-2], "an")
    if w.endswith("id"):
        if w in _ID_NOUNS or word[:1].isupper():
            return None
        return _ortho(word[:-2], "an")
    return None

# Ordered longest-first: -aréis must win before -éis.
_VOS_SUFFIX = [
    ("aríais", "arían"), ("eríais", "erían"), ("iríais", "irían"),
    ("aréis", "arán"), ("eréis", "erán"), ("iréis", "irán"),
    ("asteis", "aron"), ("isteis", "ieron"),
    ("abais", "aban"), ("íais", "ían"),
    ("arais", "aran"), ("ierais", "ieran"),
    ("áis", "an"), ("éis", "en"),
    # NOTE: no generic ("ís","en") rule -- it mangles país/París/anís.
    # The -ís verbs are listed individually in _VOS_IRREG instead.
]

def _rewrite_vosotros(text: str) -> str:
    text = re.sub(r"(?<!\w)vosotros(?!\w)", lambda m: _match_case(m.group(0), "ustedes"), text, flags=re.I)
    text = re.sub(r"(?<!\w)vosotras(?!\w)", lambda m: _match_case(m.group(0), "ustedes"), text, flags=re.I)
    for a, b in (("vuestros", "sus"), ("vuestras", "sus"),
                 ("vuestro", "su"), ("vuestra", "su")):
        text = re.sub(rf"(?<!\w){a}(?!\w)", lambda m, b=b: _match_case(m.group(0), b), text, flags=re.I)
    _vos = {**_VOS_IMPERATIVE, **_VOS_IRREG}
    for s, t in sorted(_vos.items(), key=lambda p: len(p[0]), reverse=True):
        text = re.sub(rf"(?<!\w){s}(?!\w)", lambda m, t=t: _match_case(m.group(0), t), text, flags=re.I)
    def imperative(m):
        w = m.group(0)
        if len(w) < 5:          # too short to be a safe verb guess
            return w
        r = _regular_imperative(w)
        return _match_case(w, r) if r else w
    text = re.sub(r"(?<!\w)\w+(?:ad|ed|id)(?!\w)", imperative, text)

    def suffix(m):
        w = m.group(0)
        for a, b in _VOS_SUFFIX:
            if w.lower().endswith(a) and len(w) > len(a) + 1:
                return w[: -len(a)] + b
        return w
    text = re.sub(r"(?<!\w)\w+(?:aríais|eríais|iríais|aréis|eréis|iréis|asteis|"
                  r"isteis|abais|íais|arais|ierais|áis|éis)(?!\w)",
                  suffix, text, flags=re.I)
    return text


def to_neutro(text: str) -> str:
    text = _rewrite_vosotros(text)
    text = _rewrite_verbs(text)
    text = _rewrite_nouns(text)
    return text


if __name__ == "__main__":
    cases = [
        "Tengo que encender el ordenador.",
        "Aparcamos el coche en la calle.",
        "Pon la leche en la nevera.",
        "Ayer perdí mis gafas.",
        "El fontanero arregló la tubería.",
        "Compró un billete de autobús.",
        "Mi portátil es muy ligero.",
        "Tenemos que coger el autobús.",
        "¿Todos tenéis vuestras entradas?",
        "Venid todos aquí.",
        "Aprendió a conducir el año pasado.",
        "Los ordenadores nuevos están en la mesa.",
        "Compré unas gafas oscuras.",
        "Comed la tarta y bebed el zumo.",
        "¿Dónde aparcasteis vuestros coches?",
    ]
    for c in cases:
        out = to_neutro(c)
        flag = "   " if out == c else "-> "
        print(f"{c}\n{flag}{out}\n")
