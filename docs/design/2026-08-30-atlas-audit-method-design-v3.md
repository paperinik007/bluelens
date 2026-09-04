# Metodo a 5 passi per audit basati su una tassonomia esterna (ATLAS) — Design (v3)

**Sostituisce**: `docs/design/2026-08-30-atlas-audit-method-design-v2.md` (v2), che a sua
volta sostituiva `docs/design/2026-08-29-atlas-audit-method-design.md` (v1) — nessuna
versione viene cancellata, tutte restano nel repo come storico (principio 4/7
`SPIRIT.md`).

**Esito primo council checkpoint** (roster completo skeptic/risk/pragmatist/advocate,
scope pieno, agenti user-level di questa sessione Claude, 2026-08-29/30): skeptic e risk
hanno trovato, da angolazioni indipendenti, lo stesso difetto strutturale nella regola di
stop del passo 2 (v1) — decideva quante varianti autorare **in base a un verdetto live
del detector**, in tensione diretta con `SPIRIT.md` principio 2 e principio 1. Corretto
in v2: passo 2 riscritto per non guardare mai un output di detector durante l'autoria.
v2 ha corretto anche `verified_date` (rimosso), il caveat sull'`evidence` check, il
rischio di collisione segnalato come attivo, l'istruzione `declared_scope` ammorbidita, e
due chiarimenti di leggibilità.

**Esito secondo council checkpoint, indipendente** (Pi, 4 agenti user-level separati
`council-{advocate,pragmatist,risk,skeptic}`, eseguito in parallelo sulla v1, senza
visibilità sulla v2 già in corso in questa sessione): **3 dei 4 pareri (skeptic, risk,
pragmatist) sono convergenti indipendentemente sullo stesso meccanismo già corretto in
v2** — una seconda conferma, da agenti/modelli diversi da quelli del primo council, dello
stesso difetto. Oltre a questo, il secondo council ha trovato 4 problemi nuovi, non visti
dal primo giro, **tutti verificati da questa sessione contro le fonti primarie prima di
essere accolti** (mai recepiti sulla sola fiducia nel report):
1. Il prototipo di falsificazione valida solo la *terminazione* della regola di stop, non
   l'affidabilità di un verdetto di detector reale — confermato leggendo
   `temp/atlas-variant-stopping-prototype/README.md`: "I verdetti (detected/missed) sono
   inseriti a mano dall'operatore... non esegue il toy_agent, non chiama nessun detector
   reale."
2. La voce illustrativa `aidr` in `vendor_scope_verification.yaml` non portava il caveat
   di campione minuscolo che il research doc citato dichiara esplicitamente su di sé
   (confermato leggendo `docs/research/2026-08-26-analisi-metriche-intento-vs-effetto.md`:
   "campione minuscolo (TP=1, FP=4, FN=2). I CI sono larghissimi").
3. La voce illustrativa `llamafirewall` collassava in un solo verdetto un'asimmetria che
   il research doc citato dichiara esplicitamente (confermato leggendo
   `docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md`,
   sezione "Cosa NON dice questa analisi": il meccanismo è verosimilmente in ambito per
   un tipo di attacco diverso e non testato da questo dataset, mentre è cieco proprio al
   pattern effettivamente testato qui).
4. Il campo `concordance` (v2) viveva nel posto sbagliato: `cases.yaml` è vendor-neutro
   per costruzione (Nodo B), ma "le 3 varianti concordano" è per forza un giudizio
   specifico di un vendor (un detector diverso può giudicare lo stesso cluster in modo
   diverso) — non un fatto unico da scrivere una volta sul caso condiviso. Trovato
   incrociando il punto (c) del secondo council-risk con la struttura già scritta in v2.

Tutte e quattro le correzioni sono applicate in questa revisione — vedi le note puntuali
nelle sezioni interessate sotto.

**Decisioni ereditate dalla nota di analisi preliminare (§7-8, Nodo A/B/D) e non
rimesse in discussione qui — il Nodo C è quello corretto in v2/v3, vedi sopra**:
- Nodo A: questo documento tratta **solo il metodo** — il cross-check completo
  T0001-T0014 vs MITRE ATLAS è un research doc separato, stesso pattern di
  `docs/research/2026-08-19-taxonomy-cross-check-findings.md`, e viene **dopo** questo
  documento, usando il metodo già stabile qui.
- Nodo B: "ambito dichiarato vs ambito reale" per vendor vive in una tabella catalogo
  separata, fuori da `schema.py`/`metrics.py`/`Verdict` per costruzione — stesso pattern
  di `catalog/cases.yaml` + `catalog/vendor_taxonomy_snapshot.yaml`.
- Nodo D: entra qui come sezione di estensione futura **dichiarata** (testo, non
  implementazione) — nessuna orchestrazione nuova costruita in questo documento.

## Perché questo metodo esiste

`SPIRIT.md` principio 1 (dataset indipendente) e principio 2 (metodologia dichiarata
prima dei risultati) reggevano finora solo per il primo vendor (`aidr`), il cui catalogo
di tecniche (T0001-T0014) è stato costruito a mano senza una fonte esterna mantenuta.
MITRE ATLAS offre una tassonomia AI/agentic reale e attivamente mantenuta (v5.1.0,
novembre 2025, 16 tattiche/84 tecniche) — ma trasformare un suo case study in un attacco
eseguibile contro il nostro agente resta lavoro nostro, ogni volta (stesso problema già
affrontato il 2026-08-19 per R-Judge/InjecAgent/AgentDojo/AgentHarm). Questo documento
fissa **come** si fa quel lavoro, in un modo che regge per qualunque tecnica futura presa
da ATLAS (o da qualunque altra fonte), non solo per il primo caso analizzato.

Punto centrale, già trovato due volte in questo progetto su soggetti diversi
(`aidr`/AlignmentCheck, vedi `docs/strategy/posizionamento.md` §9): l'ambito che un
vendor **dichiara** di coprire e l'ambito che il suo meccanismo **verificato** copre
davvero possono divergere. Bombardare un detector con tecniche ampie senza registrare
questa distinzione rischia di scambiare un miss strutturale (fuori dall'ambito vero) per
un fallimento del detector, o un successo casuale per una copertura che non esiste.

**Vincolo di tesi, non negoziabile in questo documento** (`posizionamento.md` §1: "non
misuriamo il modello — misuriamo il detector"): ogni scelta del metodo sotto verifica il
**detector**, mai quanto un attacco è efficace contro l'agente. Dove questa distinzione
tocca una decisione concreta (passo 2), è nominata esplicitamente.

## I 5 passi del metodo

1. **Selezione tecniche ampia, non pre-filtrata dall'ambito dichiarato dal vendor.** Se
   il filtro si applicasse qui, a monte, si potrebbe solo confermare o smentire il tool
   dentro la cornice che il vendor stesso ha scelto — mai scoprire che la cornice
   dichiarata è più generosa di quella reale, esattamente il tipo di scoperta più
   preziosa già fatta finora (AlignmentCheck). **Fuori scope qui, delegato al research
   doc** (Nodo A): il criterio di mappabilità tra una tecnica ATLAS e i 6 tool del nostro
   agente (trovato dal primo council-pragmatist — vedi "Esplicitamente fuori scope"
   sotto).
2. **Generazione di 2-3 varianti fisse, a distanza di superficie crescente** (parola →
   tool → canale, secondo quanti livelli sono genuinamente distinguibili per quella
   tecnica), **scritte ed eseguite tutte, senza mai guardare un verdetto di detector
   durante l'autoria** — dettaglio sotto.
3. **Trasformazione in attacchi eseguibili** contro l'agente reale e i tool reali —
   stessa disciplina "eseguito, non fabbricato" già in uso per l'intero dataset.
4. **Esecuzione di attacchi e dei loro gemelli benigni**, misurazione del risultato
   grezzo — stessa regola del "gemello benigno" già documentata in
   `catalog/_template.yaml`: un detector che spara a tutto avrebbe recall perfetto senza
   essere utile, quindi ogni tecnica bombardata richiede anche la sua controparte
   legittima nello stesso passo, non solo gli attacchi.
5. **Interpretazione**, confrontando il risultato grezzo con l'ambito dichiarato dal
   vendor, registrando il giudizio in `catalog/vendor_scope_verification.yaml` (Sezione
   dedicata sotto) — mai letto dal motore di scoring. **Qui, e solo qui**, un analista
   nota anche in prosa come le varianti di un cluster si sono comportate per quel
   vendor specifico (vedi passo 2).

## Passo 2 in dettaglio — 2-3 varianti fisse, decise a priori, mai da un verdetto live

**Correzione v1→v2** (primo council checkpoint, skeptic+risk convergenti): la v1
proponeva una regola adattiva (`MAJORITY_3`) che decideva **durante l'autoria** se
scrivere una terza variante, in base al verdetto del detector sulle prime due —
esattamente ciò che il principio 2 di `SPIRIT.md` vieta ("ogni caso di test viene
definito... prima di eseguire il tool, per evitare bias di conferma"), e che rischiava
di tarare il dataset condiviso tra vendor sul detector usato durante l'autoria
(principio 1). Discusso con l'utente: la proposta iniziale di correzione (usare
`attack_succeeded`, lato agente, come segnale di concordanza) è stata scartata perché
sposterebbe l'esercizio da "verifichiamo il detector" a "quanto è efficace l'attacco
contro l'agente" — la stessa linea che il Nodo D esclude esplicitamente
(`posizionamento.md` §1).

**Correzione v2→v3** (secondo council checkpoint, Pi, punti 1 e 4 sopra): v2 imponeva
sempre e solo 3 varianti fisse, e aggiungeva un campo `concordance` su `cases.yaml` per
classificare l'accordo tra le 3. Due problemi trovati e corretti qui:
- **Sempre 3 è troppo rigido**: non tutte le tecniche hanno 3 livelli di distanza
  superficiale genuinamente distinguibili (es. "tool" e "canale" possono coincidere per
  un vettore di code-execution) — forzare un terzo livello inventato produrrebbe un caso
  di bassa qualità solo per rispettare un conteggio. Corretto: il numero di varianti
  (2 o 3) è deciso **a priori, guardando solo la tecnica e lo schema di distanza
  superficiale** — mai un verdetto di detector, quindi nessuna riapertura del problema
  v1. Il prototipo non va rifatto: la sua proprietà verificata ("3 livelli bastano per il
  caso peggiore testato") resta valida per il caso a 3 livelli; il caso a 2 livelli non
  necessita di falsificazione, perché non introduce nessuno stato adattivo da
  falsificare.
- **`concordance` viveva nel posto sbagliato**: `cases.yaml` è vendor-neutro per
  costruzione (Nodo B) — condiviso tra `aidr`, `llamafirewall`, e ogni vendor futuro.
  "Le varianti di questo cluster concordano" è però un giudizio **specifico di un
  vendor**: un detector può giudicarle in modo diverso da un altro. Scrivere un solo
  valore di concordanza su un caso condiviso avrebbe forzato un'assunzione mai
  dichiarata (verdetti omogenei e comparabili tra vendor) che il codice non garantisce —
  e infatti `catalog/registro-limiti-aperti.md` registra già un vendor (LlamaFirewall)
  con output non binario (PromptGuard, ancora non attivato ma già documentato). Corretto:
  **nessun campo di concordanza su `cases.yaml`**. Il giudizio su come un vendor
  specifico si è comportato sulle varianti di un cluster va scritto in prosa dentro
  `vendor_scope_verification.yaml` (Sezione Passo 5 sotto), dove l'informazione è già
  per-vendor per costruzione.

**Regola adottata**: le varianti (2 o 3, decise a priori) sono **sempre tutte scritte ed
eseguite**, con contenuto e conteggio fissati dallo schema di distanza superficiale —
mai condizionati da un output di detector. Il caso a 3 livelli riusa `STRICT_3`,
già testata nel prototipo del 29/08 (`temp/atlas-variant-stopping-prototype/`,
gitignored, consumato) e confermata "regge sempre, combacia esattamente coi 3 livelli".
**Nota sul valore di questa verifica** (trovato dal secondo council-skeptic, verificato
leggendo il README del prototipo): il prototipo non ha mai chiamato un detector reale — i
verdetti "detected/missed" erano inseriti a mano dall'operatore per esplorare sequenze
difficili a mente. Questo valida la **terminazione della logica di stato** (la regola non
si blocca mai, dato un qualunque ingresso binario), non l'affidabilità di un verdetto di
detector reale — distinzione che la v1/v2 non rendevano esplicita. Non compromette la
correttezza della regola come scelta qui (che ora non dipende comunque da nessun
detector live), ma corregge quanto le versioni precedenti implicitamente rivendicavano
di aver dimostrato.

**Quando si applica**: solo alle tecniche autorate ex novo con questo metodo (derivate da
ATLAS o da una fonte futura equivalente) — non un retrofit dei casi già esistenti in
`catalog/cases.yaml`, che restano non clusterizzati (`variant_cluster_id: null`), come
prima di questo documento (chiarimento richiesto dal primo council-advocate).

### Dove vive il tracking (schema, `catalog/cases.yaml`)

Due campi nuovi (**non tre — `concordance` rimosso in v3**, vedi sopra), opzionali su
ogni entry — valorizzati solo quando l'entry appartiene a un cluster generato con questo
passo:

```yaml
variant_cluster_id: <string|null>   # id condiviso dalle entry sorelle dello stesso
                                     # cluster tecnica+scenario
variant_round_count: <2|3|null>     # quante varianti nel cluster — deciso a priori da
                                     # quanti livelli di distanza superficiale
                                     # (parola/tool/canale) sono genuinamente
                                     # distinguibili per QUESTA tecnica, mai da un
                                     # verdetto di detector
```

**Perché un campo strutturato e non solo prosa nel `rationale`**: senza un campo
verificabile, un'autoria futura (possibilmente delegata a un subagent, come già prassi
in questo progetto) potrebbe generare una variante in più o in meno senza dichiararlo,
senza che nessun controllo automatico se ne accorga — la stessa classe di corruzione
silenziosa che i principi 6/8 di `SPIRIT.md` vietano per il misuratore, applicata qui
all'autoria del dataset che il misuratore poi valuta.

**Limite accettato, dichiarato esplicitamente** (trovato dal primo council-risk, punto
1): il tracking resta auto-dichiarato. Un'entry che appartiene davvero a un cluster ma
omette i due campi (li lascia `null`) è indistinguibile, per qualunque test proposto
qui, da un caso singolo legittimo mai passato dal passo 2 — nessun controllo automatico
chiude questa scappatoia per costruzione, perché richiederebbe inferire l'intento
dell'autore. Accettato come limite (coerente con l'onestà statistica/dei limiti richiesta
dal principio 3 di `SPIRIT.md`), non risolto qui — una revisione umana della sessione di
autoria resta la difesa reale, non un test.

## Passo 5 in dettaglio — `catalog/vendor_scope_verification.yaml`

Nuovo file, accanto a `vendor_taxonomy_snapshot.yaml` (stesso pattern append-only di
`cases.yaml`: mai riscrivere voci esistenti). Registra, per ogni coppia
vendor+tecnica (o vendor+meccanismo, quando il finding non è legato a una singola
tecnica), cosa il vendor **dichiara** di coprire contro cosa il meccanismo **verificato**
fa davvero:

```yaml
entries:
  - vendor: aidr                          # o llamafirewall, o un vendor futuro
    technique_code: T0001                 # codice T00NN da vendor_taxonomy_snapshot.yaml
                                           # (la tassonomia condivisa del progetto, non
                                           # necessariamente quella nativa del vendor
                                           # elencato qui — LlamaFirewall non ne ha una
                                           # propria, vedi registro-limiti-aperti.md),
                                           # o null se il finding non è legato a una
                                           # singola tecnica
    declared_scope: >
      <cosa il vendor dichiara di coprire — descrizione fedele, con citazione diretta
      quando esiste una fonte puntuale per quella tecnica (es. detection_guidance);
      per un vendor senza tassonomia propria (es. LlamaFirewall), una sintesi
      verificabile del comportamento dichiarato a livello di prodotto, con la fonte
      primaria citata in evidence>
    verified_mechanism: >
      <cosa il meccanismo fa davvero, verificato leggendo il codice/prompt di sistema
      del vendor pinnato o osservando i verdetti reali. Se la fonte citata in evidence
      dichiara un limite statistico (campione piccolo, CI ampio) o un'asimmetria (il
      meccanismo può essere in ambito per un pattern di attacco diverso da quello
      verificato qui), riportare anche quello — non solo la conclusione puntuale. Se
      questo cluster proviene dal passo 2 (2-3 varianti a distanza superficiale
      crescente), notare qui esplicitamente come QUESTO vendor si è comportato su
      ciascuna variante — l'accordo/disaccordo tra varianti è un giudizio specifico di
      questo vendor, non un fatto vendor-neutro (vedi passo 2)>
    verdict: in_scope | narrower_than_declared | out_of_scope
    evidence: >
      <path del research doc o del report che ha verificato questo — mai
      un'affermazione senza fonte. Nota: la verifica automatica (test sotto) controlla
      solo che il path esista su disco, non che sostenga davvero l'affermazione — un
      lettore non deve assumere una verifica di pertinenza automatica>
```

`verdict` a 3 valori (non un booleano `in_declared_scope`, il bivio che il Nodo B ha
scartato in favore della tabella stessa): `in_scope` (il meccanismo copre quello che
dichiara), `narrower_than_declared` (dichiara un ambito ampio, il meccanismo ne copre
solo una parte), `out_of_scope` (il vendor non dichiara affatto di coprire quella
tecnica — un miss lì non è un fallimento del detector).

**Limite dichiarato, non risolto qui** (trovato indipendentemente dal primo
council-risk/advocate e dal secondo council-risk/advocate — convergenza a 4 su questo
punto, il più forte dell'intera review): append-only senza una policy di ri-verifica
significa che un'entry resta silenziosamente valida anche dopo che il vendor ha
aggiornato il prodotto — non c'è meccanismo che segnali una voce potenzialmente
obsoleta. Rimuovere `verified_date` (v2) non introduce questo rischio, lo eredita
soltanto: quel campo non aveva comunque una policy di ri-verifica associata, quindi
toglierlo non peggiora nulla. Non risolto in questo documento — una policy di
ri-verifica periodica (es. "ri-controllare ogni voce quando il pin del vendor cambia",
stesso trigger già usato per `vendor_taxonomy_snapshot.yaml`) resta un passo futuro
esplicito.

Due voci vengono popolate subito, non nuova ricerca ma trascrizione di findings già
completamente verificati nel repo — **corrette in questa revisione** per portare i
caveat che le fonti citate dichiarano esplicitamente su sé stesse (trovato dal secondo
council-skeptic, verificato contro le fonti primarie):

```yaml
  - vendor: aidr
    technique_code: null
    declared_scope: >
      aidr valuta la sessione per intento del prompt (goal hijacking) — il criterio
      pubblicato tratta l'obiettivo dichiarato dalla richiesta come segnale primario.
    verified_mechanism: >
      Il meccanismo osservato giudica il linguaggio del prompt, non l'azione effettiva
      dell'agente nel transcript — verificato caso per caso: 4 falsi positivi su
      rifiuti espliciti dell'agente, 2 falsi negativi su attacchi formulati in modo
      non aggressivo ma comunque eseguiti. Campione minuscolo (TP=1, FP=4, FN=2 sulla
      metrica "effetto", singolo run di 31 casi) — il research doc citato dichiara
      esplicitamente intervalli di confidenza larghissimi e non rivendica
      generalizzazione oltre questo run; la direzione del segnale è verificata caso per
      caso, non solo statisticamente.
    verdict: narrower_than_declared
    evidence: docs/research/2026-08-26-analisi-metriche-intento-vs-effetto.md

  - vendor: llamafirewall
    technique_code: null
    declared_scope: >
      AlignmentCheck valuta se il comportamento dell'agente persegue l'obiettivo
      complessivo della sessione (goal hijacking) — ambito dichiarato ampio, a livello
      di sessione.
    verified_mechanism: >
      Verificato sul prompt di sistema reale (vendor_proxy.jsonl catturato) e sulle
      rationale dei verdetti: il meccanismo valuta solo se l'azione corrente è coerente
      col messaggio utente immediatamente precedente — mai l'obiettivo complessivo o la
      sua legittimità. Un attacco che chiede esplicitamente un'azione dannosa in un
      turno resta invisibile per costruzione, indipendentemente da quanto l'ambito
      dichiarato sembri coprirlo. Asimmetria dichiarata esplicitamente dal research doc
      citato: il meccanismo è verosimilmente in ambito per un tipo di attacco diverso e
      non testato da questo dataset — "goal hijacking" inteso come deviazione da un
      obiettivo legittimo originale verso uno non richiesto — mentre è strutturalmente
      cieco proprio al pattern che questo dataset misura quasi esclusivamente:
      esecuzione compiacente di un'istruzione dannosa esplicita. Il verdict sotto si
      riferisce specificamente a questo secondo pattern, non a un giudizio generale sul
      prodotto.
    verdict: narrower_than_declared
    evidence: docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md
```

Test nuovo (`tests/test_catalog.py`, stesso file dei test già esistenti per
`cases.yaml`): campi obbligatori presenti su ogni entry, `technique_code` (quando non
`null`) esiste in `vendor_taxonomy_snapshot.yaml`, `verdict` è uno dei 3 valori ammessi,
`evidence` contiene un path `docs/**.md` che risolve a un file esistente su disco (stesso
principio del check `_URL_RE` già presente per `citation` su `cases.yaml`, adattato a un
path locale invece che un URL esterno — **verifica di presenza, non di pertinenza**, vedi
nota sopra). **Limite dichiarato** (trovato dal secondo council-advocate): entrambe le
voci illustrative hanno `technique_code: null`, quindi il test "`technique_code` esiste
nello snapshot" parte con **zero copertura reale** — resterà non esercitato finché una
voce futura non valorizza il campo. Non un difetto del test, ma va saputo: il test esiste
e passa oggi solo perché non ha ancora nulla da verificare per davvero.

## Falsificazione pre-council

Prototipo a perdere eseguito il 29/08 su `temp/atlas-variant-stopping-prototype/`
(gitignored, già consumato — non da rifare), caso di test T0002/`AML.CS0035`. **Nota
aggiunta in v3** (secondo council-skeptic, verificato contro il README del prototipo,
citato sopra nel passo 2): il prototipo non ha mai eseguito un detector reale — i
verdetti erano inseriti a mano per esplorare la logica di stato. La tabella sotto va
letta come falsificazione della **terminazione della regola**, non dell'affidabilità di
un giudizio di detector reale.

| Assunzione | Esperimento | Risultato | Impatto sul design |
|---|---|---|---|
| `EARLY_STOP_2` (2 concordanti fermano subito, altrimenti fino a 2 in più) non si blocca mai | Testato il caso peggiore: detected, missed, poi ancora ambiguo a 3 varianti | Si blocca per davvero — serve una 4ª variante, ma solo 3 livelli di distanza superficiale (parole/tool/canale) sono mai stati definiti. Bug reale, verificato, non ipotetico | Scartata |
| `STRICT_3` (sempre e solo 3 varianti, decidi lì) regge sempre | Testato convergente (stabile) e divergente (instabile) | Regge sempre, combacia coi 3 livelli — il "risparmio" perso (fermarsi prima se le prime 2 concordano) non è un obiettivo di questo design (vedi passo 2) | **Adottata** per il caso a 3 livelli — riletta come politica di autoria fissa (2 o 3 deciso a priori), con giudizio di concordanza scritto in prosa per-vendor al passo 5, non come campo unico su `cases.yaml` (v3) |
| `MAJORITY_3` (2 concordanti fermano subito; altrimenti la 3ª decide per maggioranza) non si blocca mai e non richiede mai una 4ª variante | Testati entrambi i rami: detected/detected → ferma a 2; detected/missed/detected → maggioranza "detected 2/3" a 3, mai esaurito | Confermata vera in entrambi i rami — ma la regola **decide se autorare la 3ª variante in base a un verdetto di detector**, in tensione coi principi 1/2 di `SPIRIT.md` (trovato indipendentemente da due council separati, 2026-08-29/30) | **Adottata in v1, scartata in v2/v3** per il motivo sopra — non un difetto del prototipo, un difetto del come la regola veniva usata in autoria |

## Requisito → Verifica

| Requisito | Verifica eseguibile |
|---|---|
| Ogni entry di `catalog/vendor_scope_verification.yaml` ha tutti i campi obbligatori | `test_catalog.py`, nuova funzione mirror di `test_every_entry_has_all_required_fields` |
| `technique_code` (quando non `null`) esiste in `vendor_taxonomy_snapshot.yaml` | `test_catalog.py`, mirror di `test_technique_name_matches_vendor_taxonomy` — **copertura reale nulla finché una voce futura non valorizza il campo** (limite dichiarato sopra) |
| `verdict` è uno dei 3 valori ammessi (`in_scope`, `narrower_than_declared`, `out_of_scope`) | `test_catalog.py` |
| `evidence` cita un path `docs/**.md` che esiste su disco (verifica di presenza, non di pertinenza — vedi nota sopra) | `test_catalog.py` |
| Entry di `cases.yaml` che condividono un `variant_cluster_id` sono in numero pari a `variant_round_count` ∈ {2, 3} (mai 1, mai ≥4) | `test_catalog.py`, nuova funzione |
| Nessun modulo in `src/toy_agent` importa da `catalog/` | Verificato per costruzione, invariato da oggi: `dataset.py::load_dataset()` legge solo `*.yaml` dentro `dataset_dir`, mai `catalog/` — nessun nuovo test necessario, stessa garanzia strutturale già in vigore per `cases.yaml`/`vendor_taxonomy_snapshot.yaml` |
| Nessun caso di test viene incluso, escluso, o classificato in modo vendor-neutro in base a un output di detector osservato durante l'autoria (principio 1/2 `SPIRIT.md`) | **Non verificabile da un test automatico** — è una proprietà del *processo* di autoria e dello *schema* (nessun campo di concordanza su `cases.yaml`, v3), non dello stato finale dei singoli file. Verificabile solo da revisione umana della sessione di autoria (limite dichiarato, vedi passo 2) |

**Esito del mapping** (per valutare se l'estensione della skill di brainstorming vale il
costo): **due council indipendenti**, su due esecuzioni separate, hanno entrambi
contestato in modo sostanziale la stessa verifica proposta in v1 (che non catturava
affatto la dipendenza da un detector live in autoria) — non un affinamento, un cambio del
meccanismo stesso. Il secondo council ha inoltre trovato 4 problemi che il primo non
aveva visto, tutti verificati e corretti qui.

## Cosa NON cambia

- `schema.py`, `metrics.py`, `Verdict` — nessuna modifica. La tabella catalogo e il
  tracking varianti restano dati di autoring/interpretazione, mai letti dal motore di
  scoring (Nodo B).
- La regola del "gemello benigno" per ogni tecnica — invariata, già documentata in
  `catalog/_template.yaml`; il passo 4 del metodo la applica, non la ridefinisce.
- Nessun campo booleano `in_declared_scope` su `Verdict` o su `TestCase` — il bivio
  originale (leggero: prosa / pesante: campo su `Verdict`) era falso; la tabella
  catalogo è la terza via già in uso nel progetto per questo tipo di giudizio.

## Esplicitamente fuori scope da questo design

- Il cross-check completo T0001-T0014 vs MITRE ATLAS — research doc separato, prossimo
  passo dopo questo documento (Nodo A). **Deve definire esplicitamente**, come suo primo
  passo, il criterio di mappabilità tra una tecnica ATLAS e i 6 tool del nostro agente
  (trovato dal primo council-pragmatist: senza un criterio dichiarato, il research doc
  rischia di spendere sforzo di autoria su tecniche non trasponibili, o di scartarne
  arbitrariamente altre che lo sarebbero) — non definito qui perché è un lavoro di
  selezione, non di meccanismo.
- Il popolamento reale di `vendor_scope_verification.yaml` oltre le due voci illustrative
  sopra (già completamente verificate da lavoro esistente) — il popolamento sistematico
  per ogni tecnica futura avviene quando il research doc/i piani successivi lo
  richiedono, non qui.
- Qualunque estensione futura del Nodo D — dichiarata come testo, non costruita.
- T0009/T0011 (Gap 17, limite dichiarato, non riaperto qui).
- Un controllo sistematico di tutte le coppie di tecniche per collisioni di segnale
  (rischio già registrato in `docs/design/registro-limiti-aperti.md` per T0005/T0010 e
  T0002/T0012) — **questo documento non solo eredita quel debito, ma può aumentarlo**
  (trovato dal primo council-risk): generare sistematicamente 2-3 varianti a distanza di
  superficie crescente per ogni tecnica ATLAS esplora attivamente lo stesso spazio che ha
  già prodotto la collisione T0002/T0012 (una variante che reintroduceva un indirizzo
  esterno). Non risolto qui — un controllo di sovrapposizione tra un nuovo cluster e le
  tecniche/segnali già esistenti resta un passo manuale della revisione, non
  automatizzato da questo design.
- Integrazione di `vendor_scope_verification.yaml` nel report pubblicato
  (`report.py`) — trovato dal primo council-advocate come lacuna reale (un lettore di un
  report non distinguerebbe da solo un miss "fuori ambito dichiarato" da un miss reale).
  Non risolto qui, per coerenza con la decisione già presa nel Nodo B: la tabella è
  "interrogata alla bisogna" (stesso pattern di `cases.yaml`, mai auto-integrata nel
  rendering), non un dato che il motore del report legge automaticamente. Resta un passo
  futuro esplicito, non un'omissione silenziosa.
- Una policy di ri-verifica periodica per `vendor_scope_verification.yaml` (trovato
  convergentemente da 4 pareri su 4 nei due council — vedi Passo 5) — resta un limite
  dichiarato, non un meccanismo costruito qui.
- Un test automatico su verdetti "omogenei per cluster" (proposto dal secondo
  council-risk) — reso superfluo dalla correzione v3 stessa: senza un campo di
  concordanza su `cases.yaml`, non c'è più uno schema rigido da testare per
  l'omogeneità; il giudizio per-vendor resta prosa in `vendor_scope_verification.yaml`.
