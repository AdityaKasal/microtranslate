/* español neutro rewriting layer — a faithful port of scripts/neutro.py.
 *
 * Engine-independent: it rewrites Spanish, so it works on output from the
 * bundled opus-mt model or from the browser's own translator.
 *
 * NOTE ON \w: Python's \w matches accented letters (á, ñ); JavaScript's does
 * not. Every word boundary here uses an explicit Unicode class so the two
 * implementations agree exactly. scripts/crosscheck.mjs asserts that.
 */
const W = '[\\p{L}\\p{N}_]';
const NB = (s) => `(?<!${W})${s}(?!${W})`;
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const rx = (s, f = 'giu') => new RegExp(s, f);

const LEX = [
  {src:["ordenador","ordenadores"], tgt:["computadora","computadoras"], sg:"m", tg:"f"},
  {src:["portátil","portátiles"], tgt:["laptop","laptops"], sg:"m", tg:"f"},
  {src:["móvil","móviles"], tgt:["celular","celulares"], sg:"m", tg:"m"},
  {src:["zumo","zumos"], tgt:["jugo","jugos"], sg:"m", tg:"m"},
  {src:["coche","coches"], tgt:["auto","autos"], sg:"m", tg:"m"},
  {src:["patata","patatas"], tgt:["papa","papas"], sg:"f", tg:"f"},
  {src:["nevera","neveras"], tgt:["refrigerador","refrigeradores"], sg:"f", tg:"m"},
  {src:["fontanero","fontaneros"], tgt:["plomero","plomeros"], sg:"m", tg:"m"},
  {src:["fontanera","fontaneras"], tgt:["plomera","plomeras"], sg:"f", tg:"f"},
  {src:["gafas"], tgt:["lentes"], sg:"f", tg:"m"},
  {src:["ascensor","ascensores"], tgt:["elevador","elevadores"], sg:"m", tg:"m"},
  {src:["tarta","tartas"], tgt:["pastel","pasteles"], sg:"f", tg:"m"},
  {src:["billete","billetes"], tgt:["boleto","boletos"], sg:"m", tg:"m"},
  {src:["melocotón","melocotones"], tgt:["durazno","duraznos"], sg:"m", tg:"m"},
  {src:["camarero","camareros"], tgt:["mesero","meseros"], sg:"m", tg:"m"},
  {src:["camarera","camareras"], tgt:["mesera","meseras"], sg:"f", tg:"f"},
  {src:["bañador","bañadores"], tgt:["traje de baño","trajes de baño"], sg:"m", tg:"m"},
  {src:["calcetines"], tgt:["medias"], sg:"m", tg:"f"},
  {src:["cerilla","cerillas"], tgt:["cerillo","cerillos"], sg:"f", tg:"m"},
  {src:["aparcamiento","aparcamientos"], tgt:["estacionamiento","estacionamientos"], sg:"m", tg:"m"},
  {src:["albaricoque","albaricoques"], tgt:["durazno","duraznos"], sg:"m", tg:"m"},
  {src:["judías verdes"], tgt:["ejotes"], sg:"f", tg:"m"},
  {src:["ordenador portátil"], tgt:["laptop"], sg:"m", tg:"f"},
];

const DET_M2F = {el:"la", los:"las", un:"una", unos:"unas", del:"de la", al:"a la",
  este:"esta", estos:"estas", ese:"esa", esos:"esas", aquel:"aquella",
  aquellos:"aquellas", otro:"otra", otros:"otras", todo:"toda", todos:"todas",
  mucho:"mucha", muchos:"muchas", poco:"poca", pocos:"pocas",
  nuestro:"nuestra", nuestros:"nuestras", "algún":"alguna", "ningún":"ninguna",
  "cuánto":"cuánta", "cuántos":"cuántas", varios:"varias", mismo:"misma",
  mismos:"mismas"};
const DET_F2M = Object.fromEntries(Object.entries(DET_M2F).map(([k,v])=>[v,k]));
DET_F2M["de la"]="del"; DET_F2M["a la"]="al";

const NOT_ADJ = new Set(("de del la el los las que y o en con por para a al no se lo su sus "+
  "mi mis tu tus como pero si cuando donde desde hasta sobre entre sin tras ya muy "+
  "más menos todo todos esto eso").split(" "));
const COPULA = "(?:es|era|está|estaba|fue|será|sería|parece|parecía|resulta|son|eran|"+
  "están|estaban|fueron|serán|parecen|quedó|quedaron)";

const PROTECTED = ["coche bomba","coches bomba","coche cama","licencia de conducir",
  "permiso de conducir","coche fúnebre"];

function matchCase(src, tgt){
  const c = src[0];
  return (c && c !== c.toLowerCase()) ? tgt[0].toUpperCase()+tgt.slice(1) : tgt;
}
function flipWord(w, to){
  if(to === "f"){
    if(w.endsWith("os")) return w.slice(0,-2)+"as";
    if(w.endsWith("o"))  return w.slice(0,-1)+"a";
  } else {
    if(w.endsWith("as")) return w.slice(0,-2)+"os";
    if(w.endsWith("a"))  return w.slice(0,-1)+"o";
  }
  return w;
}
function repairAgreement(text, noun, g){
  text = text.replace(rx(`(${esc(noun)}\\s+)(${W}+)`), (m,a,adj) =>
    (NOT_ADJ.has(adj.toLowerCase()) || adj[0] !== adj[0].toLowerCase()) ? m : a+flipWord(adj,g));
  text = text.replace(
    rx(`(${esc(noun)}\\s+${COPULA}\\s+)((?:muy|bastante|tan|poco|más|menos)\\s+)?(${W}+)`),
    (m,a,b,adj) => (NOT_ADJ.has(adj.toLowerCase()) || adj[0] !== adj[0].toLowerCase())
      ? m : a+(b||"")+flipWord(adj,g));
  return text;
}

function rewriteNouns(text){
  const saved = {};
  PROTECTED.forEach((phrase,i) => {
    const tok = `\u0000${i}\u0000`;
    text = text.replace(rx(NB(esc(phrase))), (m) => { saved[tok]=m; return tok; });
  });
  for(const e of LEX){
    const flip = e.sg !== e.tg;
    const detmap = e.sg === "m" ? DET_M2F : DET_F2M;
    e.src.forEach((s,i) => {
      const t = e.tgt[i] !== undefined ? e.tgt[i] : e.tgt[e.tgt.length-1];
      let next;
      if(flip){
        const alt = Object.keys(detmap).sort((a,b)=>b.length-a.length).map(esc).join("|");
        next = text.replace(rx(`(?<!${W})(${alt})(\\s+)${esc(s)}(?!${W})`),
          (m,d,sp) => matchCase(d, detmap[d.toLowerCase()] ?? d) + sp + t);
      } else next = text;
      next = next.replace(rx(NB(esc(s))), (m) => matchCase(m, t));
      if(next !== text && flip) next = repairAgreement(next, t, e.tg);
      text = next;
    });
  }
  for(const [tok,orig] of Object.entries(saved)) text = text.split(tok).join(orig);
  return text;
}

const AR_ENDINGS = ["ar","ando","ado","ada","ados","adas","o","as","a","amos","áis","an",
  "aba","abas","ábamos","abais","aban","é","aste","ó","asteis","aron",
  "aré","arás","ará","aremos","aréis","arán","aría","arías","aríamos","aríais","arían",
  "e","es","emos","éis","en","ara","aras","áramos","arais","aran",
  "ase","ases","ásemos","aseis","asen","ad"];
function ortho(stem, ending){
  if(ending && "eé".includes(ending[0])){
    if(stem.endsWith("c")) return stem.slice(0,-1)+"qu"+ending;
    if(stem.endsWith("g")) return stem.slice(0,-1)+"gu"+ending;
    if(stem.endsWith("z")) return stem.slice(0,-1)+"c"+ending;
  }
  return stem+ending;
}
const COGER = {coger:"tomar", cogiendo:"tomando", cogido:"tomado", cojo:"tomo",
  coges:"tomas", coge:"toma", cogemos:"tomamos", "cogéis":"toman", cogen:"toman",
  "cogía":"tomaba", "cogías":"tomabas", "cogíamos":"tomábamos", "cogían":"tomaban",
  "cogí":"tomé", cogiste:"tomaste", "cogió":"tomó", cogimos:"tomamos",
  cogisteis:"tomaron", cogieron:"tomaron", "cogeré":"tomaré", "cogerá":"tomará",
  "cogerán":"tomarán", coja:"tome", cojas:"tomes", cojan:"tomen", coged:"tomen"};

function rewriteVerbs(text){
  const table = [];
  const ss = "aparc", ts = "estacion";
  for(const e of AR_ENDINGS) table.push([ortho(ss,e), ortho(ts,e)]);
  for(const [k,v] of Object.entries(COGER)) table.push([k,v]);
  table.sort((a,b)=>b[0].length-a[0].length);
  for(const [s,t] of table)
    text = text.replace(rx(NB(esc(s))), (m) => matchCase(m, t));
  return text;
}

const VOS_IRREG = {"sois":"son","tenéis":"tienen","habéis":"han","estáis":"están",
  "vais":"van","veis":"ven","dais":"dan","sabéis":"saben","queréis":"quieren",
  "podéis":"pueden","hacéis":"hacen","decís":"dicen","venís":"vienen","oís":"oyen",
  "vivís":"viven","salís":"salen","escribís":"escriben","recibís":"reciben",
  "subís":"suben","abrís":"abren","seguís":"siguen","partís":"parten","sufrís":"sufren",
  "seréis":"serán","iréis":"irán","tendréis":"tendrán","venid":"vengan","tened":"tengan",
  "haced":"hagan","poned":"pongan","decid":"digan","salid":"salgan","oíd":"oigan",
  "sabed":"sepan","volved":"vuelvan"};
const VOS_IMPERATIVE = {comed:"coman",bebed:"beban",hablad:"hablen",escuchad:"escuchen",
  mirad:"miren",esperad:"esperen",entrad:"entren",pasad:"pasen",callad:"callen",
  ayudad:"ayuden",tomad:"tomen",dejad:"dejen",llevad:"lleven",traed:"traigan",
  leed:"lean",abrid:"abran",cerrad:"cierren",seguid:"sigan",escribid:"escriban",
  cantad:"canten",orad:"oren",rezad:"recen",perdonad:"perdonen",recordad:"recuerden",
  pensad:"piensen",buscad:"busquen",llamad:"llamen",contad:"cuenten",subid:"suban",
  bajad:"bajen",comprad:"compren",trabajad:"trabajen",descansad:"descansen",
  empezad:"empiecen",terminad:"terminen",parad:"paren",quedad:"queden",
  preparad:"preparen",recibid:"reciban",estad:"estén",alabad:"alaben",
  vivid:"vivan",servid:"sirvan",dormid:"duerman",pedid:"pidan",sentid:"sientan",
  medid:"midan",repetid:"repitan",vestid:"vistan",elegid:"elijan",corregid:"corrijan",
  partid:"partan",unid:"unan",sentaos:"siéntense",levantaos:"levántense",
  acercaos:"acérquense",arrodillaos:"arrodíllense",poneos:"pónganse",callaos:"cállense"};

const TAD_NOUNS = new Set(["libertad","voluntad","amistad","facultad","lealtad",
  "dificultad","mitad","potestad","majestad","tempestad","heredad"]);
const ED_NOUNS = new Set(["sed","red","pared","huésped","césped","usted","merced","ved"]);
const ID_NOUNS = new Set(["madrid","vid","ardid","david","cid","adid"]);

function regularImperative(word){
  const w = word.toLowerCase();
  if(w.endsWith("ad")){
    if(w.endsWith("dad") || TAD_NOUNS.has(w)) return null;
    return ortho(word.slice(0,-2), "en");
  }
  if(w.endsWith("ed")){
    if(ED_NOUNS.has(w)) return null;
    return ortho(word.slice(0,-2), "an");
  }
  if(w.endsWith("id")){
    if(ID_NOUNS.has(w) || word[0] !== word[0].toLowerCase()) return null;
    return ortho(word.slice(0,-2), "an");
  }
  return null;
}

// longest-first: -aréis must win before -éis. No generic -ís rule: it eats país.
const VOS_SUFFIX = [["aríais","arían"],["eríais","erían"],["iríais","irían"],
  ["aréis","arán"],["eréis","erán"],["iréis","irán"],["asteis","aron"],
  ["isteis","ieron"],["abais","aban"],["íais","ían"],["arais","aran"],
  ["ierais","ieran"],["áis","an"],["éis","en"]];

function rewriteVosotros(text){
  text = text.replace(rx(NB("vosotros")), m => matchCase(m,"ustedes"));
  text = text.replace(rx(NB("vosotras")), m => matchCase(m,"ustedes"));
  for(const [a,b] of [["vuestros","sus"],["vuestras","sus"],["vuestro","su"],["vuestra","su"]])
    text = text.replace(rx(NB(a)), m => matchCase(m,b));
  const vos = {...VOS_IMPERATIVE, ...VOS_IRREG};
  for(const s of Object.keys(vos).sort((a,b)=>b.length-a.length))
    text = text.replace(rx(NB(esc(s))), m => matchCase(m, vos[s]));
  text = text.replace(rx(`(?<!${W})${W}+(?:ad|ed|id)(?!${W})`, 'gu'), (w) => {
    if(w.length < 5) return w;
    const r = regularImperative(w);
    return r ? matchCase(w, r) : w;
  });
  text = text.replace(
    rx(`(?<!${W})${W}+(?:aríais|eríais|iríais|aréis|eréis|iréis|asteis|isteis|abais|íais|arais|ierais|áis|éis)(?!${W})`),
    (w) => {
      for(const [a,b] of VOS_SUFFIX)
        if(w.toLowerCase().endsWith(a) && w.length > a.length+1) return w.slice(0,-a.length)+b;
      return w;
    });
  return text;
}

export function toNeutro(text){
  text = rewriteVosotros(text);
  text = rewriteVerbs(text);
  text = rewriteNouns(text);
  return text;
}
