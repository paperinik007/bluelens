# agentic-security-audits

Un ente di audit indipendente per prodotti "agentic threat detection" (vedi `SPIRIT.md`): metodologia dichiarata, dataset propri, risultati pubblicati per intero, mai un benchmark self-reported dal vendor stesso.

## Language

**Vendor**:
L'organizzazione/entità che produce un tool sotto audit (es. Meta, FareedKhan-dev). Concetto descrittivo, oggi senza campo strutturato dedicato nello schema — vive in prosa/provenance finché non serve distinguerlo formalmente dal tool.
_Avoid_: Fornitore, produttore (usare sempre "vendor" per coerenza con SPIRIT.md, che lo usa già al plurale)

**Tool** (campo schema: `Verdict.tool_name`):
Il prodotto specifico misurato — quello che determina un set distinto di numeri nel report. Non coincide necessariamente col vendor: un vendor può pubblicare più tool distinti (es. LlamaFirewall di Meta bundla AlignmentCheck/PromptGuard2/CodeShield come scanner indipendenti — ognuno, se auditato separatamente, è un tool distinto con proprio `tool_name`). Il rapporto vendor:tool è 1:1 solo per coincidenza nei due audit attuali, non per garanzia strutturale.
_Avoid_: Non usare "tool" per riferirsi a una chiamata funzione/API dentro una traiettoria dell'agente — quello è `ToolCall` (`schema.py:13`), un concetto diverso e già esistente nel codice, che condivide per sfortuna lo stesso nome di campo (`tool_name`) ma non ha nulla a che fare col detector.

**Nomi di tool risolti**:
- aidr → `tool_name = "aidr"` (non `"agentic_threat_detection"`, che era il nome del repo del vendor, non del prodotto). Nessun suffisso: Sifter/Inspector/Gauntlet girano come un'unica pipeline combinata (`Pipeline().analyze()`), non sono alternative selezionabili — un suffisso oggi sarebbe precisione inventata senza un referente reale.
- LlamaFirewall/AlignmentCheck → `tool_name = "llamafirewall-alignmentcheck"`. Suffisso necessario da subito: AlignmentCheck è uno scanner indipendente e selezionabile tra più scanner dello stesso pacchetto (PromptGuard2, CodeShield) — un futuro audit di uno di quegli altri scanner avrebbe un `tool_name` diverso pur restando lo stesso pacchetto/container (`vendors/llamafirewall/`, `detector-llamafirewall`, che restano nomi generici a livello di ambiente/libreria condivisa).
