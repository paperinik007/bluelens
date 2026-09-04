# Metodo a 5 passi per audit basati su una tassonomia esterna (ATLAS) — Design (v2)

**Sostituisce**: `docs/design/2026-08-29-atlas-audit-method-design.md` (v1, non committata — resta nel
repo come storico della bozza pre-council, principio 4/7 `SPIRIT.md`: nessuna versione
scompare, non sostituita silenziosamente).

**Esito council checkpoint** (roster completo skeptic/risk/pragmatist/advocate, scope
pieno, 2026-08-29/30): skeptic e risk hanno trovato, da angolazioni indipendenti, lo
stesso difetto strutturale nella regola di stop del passo 2 — la v1 decideva quante
varianti autorare **in base a un verdetto live del detector**, in tensione diretta con
`SPIRIT.md` principio 2 ("ogni caso di test viene definito... prima di eseguire il tool,
per evitare bias di conferma") e con principio 1 (il dataset condiviso tra vendor
finirebbe tarato sul detector usato durante l'autoria). Corretto in questa revisione:
passo 2 ora scrive sempre 3 varianti fisse, senza mai guardare un output di detector
durante l'autoria — dettaglio sotto. Risk ha trovato altri tre difetti minori (campo
`verified_date` non applicato, controllo `evidence` più debole di quanto il testo
originale lasciasse intendere, rischio di collisione di segnale non segnalato come
attivo) e pragmatist un quarto (`verified_date` da tagliare, stessa conclusione di
risk). Advocate ha trovato due lacune di leggibilità (quando si applica la generazione a
3 varianti, come clusters e tabella ambito si relazionano). Tutti i punti sono corretti
in questa revisione — vedi le note puntuali nelle sezioni interessate sotto.

**Decisioni ereditate dalla nota di analisi preliminare (§7-8, Nodo A/B/D) e non
rimesse in discussione qui — il Nodo C è quello corretto in questa revisione, vedi
sopra**:
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
   agente (trovato da pragmatist — vedi "Esplicitamente fuori scope" sotto).
2. **Generazione di 3 varianti fisse, a distanza di superficie crescente** (parola → tool
   → canale), **scritte ed eseguite tutte, senza mai guardare un verdetto di detector
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
   dedicata sotto) — mai letto dal motore di scoring. **Qui, e solo qui**, si calcola
   anche la classificazione di concordanza delle 3 varianti (vedi passo 2).

## Passo 2 in dettaglio — 3 varianti fisse, classificazione a posteriori

**Correzione rispetto alla v1** (council checkpoint, skeptic+risk convergenti): la v1
proponeva una regola adattiva (`MAJORITY_3`) che decideva **durante l'autoria** se
scrivere una terza variante, in base al verdetto del detector sulle prime due. Skeptic ha
trovato che questo è esattamente ciò che il principio 2 di `SPIRIT.md` vieta ("ogni caso
di test viene definito... prima di eseguire il tool, per evitare bias di conferma
nell'interpretazione dell'output") — l'esistenza stessa della terza variante nel dataset
permanente e condiviso tra vendor dipendeva da un output di tool osservato durante
l'autoria. Risk ha trovato, indipendentemente, che lo stesso meccanismo espone il metodo
al rumore del giudice LLM del vendor (un `stopping_reason` poteva registrare
non-determinismo del giudice invece di una vera proprietà della tecnica, senza modo di
distinguerli). Discusso con l'utente: la proposta iniziale di correzione (usare
`attack_succeeded`, lato agente, come segnale di concordanza) è stata scartata perché
sposterebbe l'esercizio da "verifichiamo il detector" a "quanto è efficace l'attacco
contro l'agente" — la stessa linea che il Nodo D esclude esplicitamente per lo stesso
motivo (`posizionamento.md` §1).

**Regola adottata**: le 3 varianti (parola/tool/canale) sono **sempre tutte scritte ed
eseguite**, con contenuto fissato dallo schema di distanza superficiale — mai
condizionato da un output di detector. Non è una regola nuova da falsificare: è
`STRICT_3`, una delle tre regole già testate nel prototipo a perdere del 29/08
(`temp/atlas-variant-stopping-prototype/`, gitignored, consumato) — scartata allora solo
per il risparmio perso rispetto a `MAJORITY_3` ("perde il risparmio 'fermati prima se le
prime 2 concordano'"), un costo che qui non conta più: l'obiettivo non è più minimizzare
lo sforzo di autoria a ogni costo, ma restare dentro i principi 1/2. `STRICT_3` "regge
sempre, combacia esattamente coi 3 livelli" — proprietà già verificata eseguendo, non
solo discussa (vedi tabella di falsificazione sotto, invariata nel merito).

La classificazione (`unanimous` se le 3 varianti concordano, `majority` se 2 su 3) si
calcola **solo al passo 5**, in fase di interpretazione, sugli stessi 3 casi già fissati
— mai come cancello che decide se un caso esiste. Con 3 campioni binari una maggioranza
esiste sempre (nessun pareggio possibile), stessa proprietà già verificata nel
prototipo. Questo chiude anche il punto di risk sul non-determinismo del giudice: un
giudice rumoroso può cambiare **come descriviamo** un cluster dopo il fatto, mai **quali
casi** finiscono nel dataset.

**Quando si applica**: solo alle tecniche autorate ex novo con questo metodo (derivate da
ATLAS o da una fonte futura equivalente) — non un retrofit dei casi già esistenti in
`catalog/cases.yaml`, che restano non clusterizzati (`variant_cluster_id: null`), come
prima di questo documento (chiarimento richiesto da advocate).

### Dove vive il tracking (schema, `catalog/cases.yaml`)

Tre campi nuovi, opzionali su ogni entry — valorizzati solo quando l'entry appartiene a
un cluster di 3 varianti generato con questo passo:

```yaml
variant_cluster_id: <string|null>   # id condiviso dalle 3 entry sorelle dello stesso
                                     # cluster tecnica+scenario
variant_round_count: <3|null>       # sempre 3 quando il cluster esiste (metodo v2 — la
                                     # v1 permetteva 2 o 3, corretto insieme al resto del
                                     # passo 2)
concordance: <unanimous|majority|null>   # calcolato al passo 5, mai in autoria — vedi
                                          # sopra. "unanimous" se le 3 varianti hanno lo
                                          # stesso verdetto, "majority" altrimenti
```

**Perché un campo strutturato e non solo prosa nel `rationale`**: senza un campo
verificabile, un'autoria futura (possibilmente delegata a un subagent, come già prassi
in questo progetto) potrebbe generare una 4ª variante o fermarsi a 1/2 senza che nessun
controllo automatico se ne accorga — la stessa classe di corruzione silenziosa che i
principi 6/8 di `SPIRIT.md` vietano per il misuratore, applicata qui all'autoria del
dataset che il misuratore poi valuta.

**Limite accettato, dichiarato esplicitamente** (trovato da council-risk, punto 1): il
tracking resta auto-dichiarato. Un'entry che appartiene davvero a un cluster ma omette i
tre campi (li lascia `null`) è indistinguibile, per qualunque test proposto qui, da un
caso singolo legittimo mai passato dal passo 2 — nessun controllo automatico chiude
questa scappatoia per costruzione, perché richiederebbe inferire l'intento
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
      primaria citata in evidence — non serve una citazione letterale se non esiste una
      singola frase da citare, ma la sintesi deve restare verificabile contro evidence>
    verified_mechanism: >
      <cosa il meccanismo fa davvero, verificato leggendo il codice/prompt di sistema
      del vendor pinnato o osservando i verdetti reali>
    verdict: in_scope | narrower_than_declared | out_of_scope
    evidence: >
      <path del research doc o del report che ha verificato questo — mai
      un'affermazione senza fonte. Nota: la verifica automatica (test sotto) controlla
      solo che il path esista su disco, non che sostenga davvero l'affermazione — un
      lettore non deve assumere una verifica di pertinenza automatica>
```

(**Corretto rispetto alla v1**: campo `verified_date` rimosso — pragmatist e risk hanno
trovato indipendentemente che non porta valore senza una policy di ri-verifica associata;
la data di pubblicazione del research doc citato in `evidence` copre la stessa esigenza,
senza un campo in più da mantenere.)

`verdict` a 3 valori (non un booleano `in_declared_scope`, il bivio che il Nodo B ha
scartato in favore della tabella stessa): `in_scope` (il meccanismo copre quello che
dichiara), `narrower_than_declared` (dichiara un ambito ampio, il meccanismo ne copre
solo una parte), `out_of_scope` (il vendor non dichiara affatto di coprire quella
tecnica — un miss lì non è un fallimento del detector).

**Relazione con i cluster di varianti del passo 2** (chiarimento richiesto da advocate):
un giudizio di ambito qui è per vendor+tecnica, non per singola variante — copre
l'intero cluster di 3 varianti generato al passo 2 per quella tecnica, non tre giudizi
separati. Se le 3 varianti hanno `concordance: majority` (non tutte concordano), il
giudizio di ambito registrato qui va scritto tenendo conto di questa non-unanimità
(es. `verified_mechanism` può nominare esplicitamente quale distanza di superficie ha
rotto il pattern), non ignorandola.

Due voci vengono popolate subito, non nuova ricerca ma trascrizione di findings già
completamente verificati nel repo:

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
      non aggressivo ma comunque eseguiti.
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
      dichiarato sembri coprirlo.
    verdict: narrower_than_declared
    evidence: docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md
```

Test nuovo (`tests/test_catalog.py`, stesso file dei test già esistenti per
`cases.yaml`): campi obbligatori presenti su ogni entry, `technique_code` (quando non
`null`) esiste in `vendor_taxonomy_snapshot.yaml`, `verdict` è uno dei 3 valori ammessi,
`evidence` contiene un path `docs/**.md` che risolve a un file esistente su disco (stesso
principio del check `_URL_RE` già presente per `citation` su `cases.yaml`, adattato a un
path locale invece che un URL esterno — **verifica di presenza, non di pertinenza**, vedi
nota sopra).

## Falsificazione pre-council

Prototipo a perdere eseguito il 29/08 su `temp/atlas-variant-stopping-prototype/`
(gitignored, già consumato — non da rifare), caso di test T0002/`AML.CS0035`. Tabella
invariata rispetto alla v1 nel merito (il prototipo non è stato rifatto); cambia solo
quale riga il documento adotta, per la ragione spiegata nel passo 2 sopra.

| Assunzione | Esperimento | Risultato | Impatto sul design |
|---|---|---|---|
| `EARLY_STOP_2` (2 concordanti fermano subito, altrimenti fino a 2 in più) non si blocca mai | Testato il caso peggiore: detected, missed, poi ancora ambiguo a 3 varianti | Si blocca per davvero — serve una 4ª variante, ma solo 3 livelli di distanza superficiale (parole/tool/canale) sono mai stati definiti. Bug reale, verificato, non ipotetico | Scartata |
| `STRICT_3` (sempre e solo 3 varianti, decidi lì) regge sempre | Testato convergente (stabile) e divergente (instabile) | Regge sempre, combacia coi 3 livelli — il "risparmio" perso (fermarsi prima se le prime 2 concordano) non è più un obiettivo di questo design (vedi passo 2, correzione v2) | **Adottata in v2** — riletta come politica di autoria fissa, con classificazione calcolata a posteriori, non come cancello di autoria |
| `MAJORITY_3` (2 concordanti fermano subito; altrimenti la 3ª decide per maggioranza) non si blocca mai e non richiede mai una 4ª variante | Testati entrambi i rami: detected/detected → ferma a 2; detected/missed/detected → maggioranza "detected 2/3" a 3, mai esaurito | Confermata vera in entrambi i rami — ma la regola **decide se autorare la 3ª variante in base a un verdetto di detector**, in tensione coi principi 1/2 di `SPIRIT.md` (trovato da council-skeptic/risk, 2026-08-29/30) | **Adottata in v1, scartata in v2** per il motivo sopra — non un difetto del prototipo, un difetto del come la regola veniva usata in autoria |

## Requisito → Verifica

| Requisito | Verifica eseguibile |
|---|---|
| Ogni entry di `catalog/vendor_scope_verification.yaml` ha tutti i campi obbligatori | `test_catalog.py`, nuova funzione mirror di `test_every_entry_has_all_required_fields` |
| `technique_code` (quando non `null`) esiste in `vendor_taxonomy_snapshot.yaml` | `test_catalog.py`, mirror di `test_technique_name_matches_vendor_taxonomy` |
| `verdict` è uno dei 3 valori ammessi (`in_scope`, `narrower_than_declared`, `out_of_scope`) | `test_catalog.py` |
| `evidence` cita un path `docs/**.md` che esiste su disco (verifica di presenza, non di pertinenza — vedi nota sopra) | `test_catalog.py` |
| Entry di `cases.yaml` che condividono un `variant_cluster_id` sono **esattamente 3** (mai 1, 2, o ≥4) | `test_catalog.py`, nuova funzione — vincolo più stretto della v1 (che ammetteva 2 o 3), corretto insieme al resto del passo 2 |
| `concordance` è coerente con i 3 verdetti effettivi del cluster quando calcolato (`unanimous` solo se tutti e 3 concordano, `majority` altrimenti) | `test_catalog.py`, nuova funzione |
| Nessun modulo in `src/toy_agent` importa da `catalog/` | Verificato per costruzione, invariato da oggi: `dataset.py::load_dataset()` legge solo `*.yaml` dentro `dataset_dir`, mai `catalog/` — nessun nuovo test necessario, stessa garanzia strutturale già in vigore per `cases.yaml`/`vendor_taxonomy_snapshot.yaml` |
| Nessun caso di test viene incluso o escluso dal dataset in base a un output di detector osservato durante l'autoria (principio 1/2 `SPIRIT.md`) | **Non verificabile da un test automatico** — è una proprietà del *processo* di autoria (i 3 file vengono scritti ed eseguiti tutti, sempre), non dello stato finale dei file, che è identico a quello prodotto da qualunque altro processo. Verificabile solo da revisione umana della sessione di autoria (limite dichiarato, vedi passo 2) |

**Esito del mapping** (per valutare se l'estensione della skill di brainstorming vale il
costo): il council checkpoint su questo documento **ha contestato una verifica proposta**
in modo sostanziale — la v1 non aveva alcuna riga che catturasse la dipendenza da un
detector live in autoria, perché la v1 stessa non la vedeva come un problema. Non un
semplice affinamento: ha cambiato il meccanismo del passo 2, non solo il suo test.

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
  (trovato da council-pragmatist: senza un criterio dichiarato, il research doc rischia
  di spendere sforzo di autoria su tecniche non trasponibili, o di scartarne
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
  (trovato da council-risk): generare sistematicamente 3 varianti a distanza di
  superficie crescente per ogni tecnica ATLAS esplora attivamente lo stesso spazio che ha
  già prodotto la collisione T0002/T0012 (una variante che reintroduceva un indirizzo
  esterno). Non risolto qui — un controllo di sovrapposizione tra un nuovo cluster e le
  tecniche/segnali già esistenti resta un passo manuale della revisione, non
  automatizzato da questo design.
- Integrazione di `vendor_scope_verification.yaml` nel report pubblicato
  (`report.py`) — trovato da council-advocate come lacuna reale (un lettore di un report
  non distinguerebbe da solo un miss "fuori ambito dichiarato" da un miss reale). Non
  risolto qui, per coerenza con la decisione già presa nel Nodo B: la tabella è
  "interrogata alla bisogna" (stesso pattern di `cases.yaml`, mai auto-integrata nel
  rendering), non un dato che il motore del report legge automaticamente. Resta un passo
  futuro esplicito, non un'omissione silenziosa.
