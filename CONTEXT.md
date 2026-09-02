# agentic-security-audits

Un ente di audit indipendente per prodotti "agentic threat detection" (vedi `SPIRIT.md`): metodologia dichiarata, dataset propri, risultati pubblicati per intero, mai un benchmark self-reported dal vendor stesso.

## Language

**Vendor**:
L'organizzazione/entità che produce un tool sotto audit (es. Meta, FareedKhan-dev). Concetto descrittivo, oggi senza campo strutturato dedicato nello schema — vive in prosa/provenance finché non serve distinguerlo formalmente dal tool.
_Avoid_: Fornitore, produttore (usare sempre "vendor" per coerenza con SPIRIT.md, che lo usa già al plurale)

**Tool** (campo schema: `Verdict.tool_name`):
Il prodotto specifico misurato — quello che determina un set distinto di numeri nel report. Non coincide necessariamente col vendor: un vendor può pubblicare più tool distinti (es. LlamaFirewall di Meta bundla AlignmentCheck/PromptGuard2/CodeShield come scanner indipendenti — ognuno, se auditato separatamente, è un tool distinto con proprio `tool_name`). Il rapporto vendor:tool è 1:1 solo per coincidenza nei due audit attuali, non per garanzia strutturale.
_Avoid_: Non usare "tool" per riferirsi a una chiamata funzione/API dentro una traiettoria dell'agente — quello è `ToolCall` (`schema.py:13`), un concetto diverso e già esistente nel codice, che condivide per sfortuna lo stesso nome di campo (`tool_name`) ma non ha nulla a che fare col detector.

**T-code**:
Codice di una tecnica secondo la tassonomia interna del vendor sotto audit (es. aidr:
`T0001`-`T0014`, in `catalog/vendor_taxonomy_snapshot.yaml`). Namespace piccolo e
specifico del vendor — due vendor diversi possono avere lo stesso numero per tecniche
completamente diverse.
_Avoid_: "codice tecnica" da solo, senza specificare se è un T-code vendor o un codice
ATLAS — ambiguo, e i due namespace collidono numericamente (es. aidr `T0006` =
"Unauthorized Resource Access", tutt'altra cosa da `AML.T0006` = "Active Scanning").

**Codice ATLAS** (`AML.T####`):
Codice di una tecnica secondo la tassonomia esterna MITRE ATLAS
(`dist/v6/ATLAS-2026.07.yaml`), indipendente da ogni vendor. Va sempre citato col
prefisso `AML.` — mai come numero nudo — per non collidere visivamente con un T-code
vendor che condivide lo stesso numero.
_Avoid_: `T0006`, `T0012` ecc. senza prefisso quando il riferimento è ad ATLAS; sempre
`AML.T0006`, `AML.T0012`.

**Nomi di tool risolti**:
- aidr → `tool_name = "aidr"` (non `"agentic_threat_detection"`, che era il nome del repo del vendor, non del prodotto). Nessun suffisso: Sifter/Inspector/Gauntlet girano come un'unica pipeline combinata (`Pipeline().analyze()`), non sono alternative selezionabili — un suffisso oggi sarebbe precisione inventata senza un referente reale.
- LlamaFirewall/AlignmentCheck → `tool_name = "llamafirewall-alignmentcheck"`. Suffisso necessario da subito: AlignmentCheck è uno scanner indipendente e selezionabile tra più scanner dello stesso pacchetto (PromptGuard2, CodeShield) — un futuro audit di uno di quegli altri scanner avrebbe un `tool_name` diverso pur restando lo stesso pacchetto/container (`vendors/llamafirewall/`, `detector-llamafirewall`, che restano nomi generici a livello di ambiente/libreria condivisa).
- LlamaFirewall combinato (AlignmentCheck + PromptGuard2 fusi in un solo Verdict, decisione 2026-09-01: `docs/design/2026-09-01-llamafirewall-promptguard-design.md`) → `tool_name = "llamafirewall-combined"`. Confermato qui il principio già scritto sopra: un audit che misura il prodotto come combinazione di più scanner è anch'esso "il prodotto specifico misurato" nel senso di questa voce — un terzo `tool_name` distinto, mai una ridefinizione di `llamafirewall-alignmentcheck` (che resta un audit a sé, invariato). `llamafirewall-alignmentcheck` e `llamafirewall-combined` restano comparabili l'uno con l'altro solo come misure di prodotti diversi (uno scanner vs due fusi), mai come lo stesso tool prima/dopo un cambiamento. Un futuro report di questo vendor va salvato sotto `docs/reports/llamafirewall-combined-YYYY-MM-DD/`, mai `docs/reports/llamafirewall-YYYY-MM-DD/` (che resta riservato ad `llamafirewall-alignmentcheck`) — stessa convenzione di naming già in uso per `aidr-YYYY-MM-DD`/`llamafirewall-YYYY-MM-DD`, così la distinzione tra i due tool è visibile dal nome della directory senza dover leggere il report o il codice (finding advocate, council 2026-09-01).
