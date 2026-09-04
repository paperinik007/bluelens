# Metodo a 5 passi per audit basati su una tassonomia esterna (ATLAS) — Design (v4)

**Sostituisce**: `docs/design/2026-08-30-atlas-audit-method-design-v3.md` (v3), che a sua
volta sostituiva v2 e v1 — nessuna versione viene cancellata, tutte restano nel repo come
storico (principio 4/7 `SPIRIT.md`).

**Esito primo e secondo council checkpoint**: vedi v3 per il dettaglio completo. In
sintesi — primo giro (skeptic+risk): corretta la regola di stop del passo 2 (v1→v2),
tolta la dipendenza da un verdetto live di detector durante l'autoria. Secondo giro (Pi,
4 agenti indipendenti, stesso roster): confermato il primo finding da modelli diversi,
più 4 correzioni minori (caveat statistici sulle 2 voci illustrative, campo
`verified_date` rimosso, rischio di collisione dichiarato attivo, criterio di
mappabilità ATLAS delegato esplicitamente al research doc).

**Esito terzo council checkpoint** (Pi, stesso roster, terzo grill indipendente su v3,
2026-08-30): nessun "approve" pieno. Verificato fattualmente (confermato da questa
sessione aprendo il repo): `catalog/vendor_scope_verification.yaml` non esiste ancora su
disco, `test_catalog.py` non cita nessuno dei campi nuovi — il mapping Requisito→Verifica
descrive test **futuri**, non già scritti (normale per un design doc non ancora passato
da un piano di implementazione, ma non dichiarato esplicitamente in v3 — corretto sotto).
Quattro punti sostanziali, valutati uno per uno, non recepiti in blocco:

1. **Accolto**: la rimozione di `concordance` da `cases.yaml` (v3) era una
   sovra-correzione. La mia obiezione originale (un valore singolo su un file
   vendor-neutro non ha senso) restava valida, ma la soluzione giusta — proposta da
   council-skeptic — era renderlo un **dizionario per-vendor**, non eliminarlo. Corretto
   sotto.
2. **Accolto in versione più stretta**: council-advocate ha ragione che "2 o 3 varianti,
   deciso a priori" (v3) non dà un criterio positivo — solo cosa NON usare (un verdetto
   di detector). Aggiunto un criterio esplicito sotto.
3. **Respinto in parte**: council-skeptic sostiene che "2 o 3 deciso a priori" sia
   *ugualmente* auto-dichiarato quanto lo era `MAJORITY_3`, quindi la garanzia di v3
   sarebbe sopravvalutata. Non concordo sull'equivalenza — vedi il disaccordo motivato
   nella sezione Passo 2 sotto. Non è stato recepito, ma non è nemmeno ignorato: è
   registrato come disaccordo esplicito, non come punto silenziosamente scartato.
4. **Accolto**: il debito cumulativo (4 limiti dichiarati "non risolti qui" attraverso
   tre revisioni) va reso esplicito come tale, non lasciato implicito nelle singole
   sezioni. Sezione dedicata aggiunta sotto.

**Decisioni ereditate dalla nota di analisi preliminare originale (§7-8, Nodo A/B/D)
e non rimesse in discussione qui**:
- Nodo A: questo documento tratta **solo il metodo** — il cross-check completo
  T0001-T0014 vs MITRE ATLAS è un research doc separato, e viene **dopo** questo
  documento, usando il metodo già stabile qui.
- Nodo B: "ambito dichiarato vs ambito reale" per vendor vive in una tabella catalogo
  separata, fuori da `schema.py`/`metrics.py`/`Verdict` per costruzione.
- Nodo D: entra qui come sezione di estensione futura **dichiarata** (testo, non
  implementazione).

## Perché questo metodo esiste

`SPIRIT.md` principio 1 (dataset indipendente) e principio 2 (metodologia dichiarata
prima dei risultati) reggevano finora solo per il primo vendor (`aidr`), il cui catalogo
di tecniche (T0001-T0014) è stato costruito a mano senza una fonte esterna mantenuta.
MITRE ATLAS offre una tassonomia AI/agentic reale e attivamente mantenuta (v5.1.0,
novembre 2025, 16 tattiche/84 tecniche) — ma trasformare un suo case study in un attacco
eseguibile contro il nostro agente resta lavoro nostro, ogni volta. Questo documento
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
**detector**, mai quanto un attacco è efficace contro l'agente.

## I 5 passi del metodo

1. **Selezione tecniche ampia, non pre-filtrata dall'ambito dichiarato dal vendor.**
   **Fuori scope qui, delegato al research doc** (Nodo A): il criterio di mappabilità tra
   una tecnica ATLAS e i 6 tool del nostro agente.
2. **Generazione di 2-3 varianti fisse, a distanza di superficie crescente** (parola →
   tool → canale, secondo un criterio esplicito — dettaglio sotto), **scritte ed eseguite
   tutte, senza mai guardare un verdetto di detector durante l'autoria**.
3. **Trasformazione in attacchi eseguibili** contro l'agente reale e i tool reali —
   stessa disciplina "eseguito, non fabbricato" già in uso per l'intero dataset.
4. **Esecuzione di attacchi e dei loro gemelli benigni**, misurazione del risultato
   grezzo — stessa regola del "gemello benigno" già documentata in
   `catalog/_template.yaml`.
5. **Interpretazione**, confrontando il risultato grezzo con l'ambito dichiarato dal
   vendor, registrando il giudizio in `catalog/vendor_scope_verification.yaml` — mai
   letto dal motore di scoring.

## Passo 2 in dettaglio — 2-3 varianti fisse, criterio esplicito, mai un verdetto live

**Storico delle correzioni** (v1→v4, riassunto — dettaglio completo in v2/v3): v1
proponeva `MAJORITY_3`, una regola adattiva che decideva **durante l'autoria** se
scrivere una terza variante in base al verdetto del detector sulle prime due — in
tensione coi principi 1/2 di `SPIRIT.md`. v2/v3 hanno corretto questo: le varianti (2 o
3) sono ora sempre scritte ed eseguite per intero, senza mai guardare un output di
detector durante l'autoria.

### Criterio positivo per "2 o 3 varianti" (nuovo in v4)

**Trovato mancante da council-advocate** (terzo giro): v3 diceva solo cosa non usare
(un verdetto di detector) per decidere il conteggio, non un criterio positivo per
riconoscere quando i 3 livelli sono genuinamente distinguibili — rischio di decisioni
incoerenti tra sessioni di autoria diverse, la stessa causa che ha già prodotto le
collisioni T0005/T0010 e T0002/T0012 (`registro-limiti-aperti.md`).

Criterio adottato: il livello **parola** (riformulare la stessa richiesta) è sempre
disponibile per costruzione — ogni tecnica ha almeno questa variante. Il livello **tool**
si aggiunge se esiste un tool o un argomento alternativo tra i 6 disponibili
(`tools.py`) che ottiene lo stesso effetto della tecnica. Il livello **canale** si
aggiunge se esiste un vettore di ingresso alternativo, distinto da quello del livello
tool — tipicamente: richiesta diretta nel turno utente vs. istruzione nascosta in un
contenuto non fidato letto da un tool (`read_ticket_content`, un campo di
`query_customer_db`). **3 varianti solo se entrambe le leve aggiuntive (tool e canale)
si applicano davvero e sono genuinamente distinte l'una dall'altra**; 2 se solo una si
applica (o se le due coincidono, es. un vettore di code-execution dove tool e canale
sono la stessa cosa — caso nominato esplicitamente da council-advocate).

### Disaccordo dichiarato, non recepito (council-skeptic, terzo giro)

Skeptic sostiene che questo criterio sia comunque "ugualmente auto-dichiarato" di quanto
lo fosse `MAJORITY_3`, perché resta un giudizio dell'autore — e che il corpo del
documento "vende" una garanzia più stretta di quanto il limite ammetta. **Non concordo
sull'equivalenza**, per una ragione precisa: il difetto di v1 non era "è un giudizio
umano" — è che il giudizio dipendeva **causalmente da un output di tool osservato
durante l'autoria** (bias di conferma, principio 2 `SPIRIT.md`). Il criterio qui sopra
è un giudizio sulla **struttura della tecnica stessa**, fatto guardando solo `tools.py`
e lo scenario — mai un'esecuzione. Se ogni giudizio umano contasse come sospetto quanto
un feedback loop reattivo su un output osservato, l'intera disciplina "definito prima di
eseguire" di questo progetto (che include, ad esempio, la scrittura di
`attack_success_criteria`) sarebbe ugualmente compromessa — un argomento che prova
troppo. Resta vero, ed è la parte del punto di skeptic che accolgo (vedi criterio
positivo sopra), che un criterio più esplicito riduce il margine di giudizio arbitrario
rispetto a "deciso a priori" nudo.

**Quando si applica**: solo alle tecniche autorate ex novo con questo metodo — non un
retrofit dei casi già esistenti in `catalog/cases.yaml`, che restano non clusterizzati
(`variant_cluster_id: null`).

### Dove vive il tracking (schema, `catalog/cases.yaml`)

Due campi, opzionali su ogni entry — valorizzati solo quando l'entry appartiene a un
cluster generato con questo passo:

```yaml
variant_cluster_id: <string|null>   # id condiviso dalle entry sorelle dello stesso
                                     # cluster tecnica+scenario
variant_round_count: <2|3|null>     # quante varianti nel cluster — deciso dal criterio
                                     # esplicito sopra (parola sempre; +tool se un tool/
                                     # argomento alternativo esiste; +canale se un
                                     # vettore di ingresso alternativo e distinto
                                     # esiste), mai da un verdetto di detector
```

**Correzione v3→v4** (secondo/terzo giro, skeptic+risk convergenti su questo punto,
angolazioni diverse): v3 aveva anche rimosso un terzo campo, `concordance`, che
classificava l'accordo tra le varianti — argomento corretto in astratto (`cases.yaml` è
vendor-neutro, "le varianti concordano" è per forza un giudizio di un vendor specifico)
ma con un rimedio sbagliato: **eliminare il campo invece di renderlo per-vendor**.
Council-skeptic (terzo giro) ha proposto l'alternativa corretta, accolta qui:

```yaml
per_vendor_concordance:             # dizionario, non un valore singolo — una chiave per
                                     # ogni vendor il cui audit ha già misurato questo
                                     # cluster; assente/vuoto finché nessun audit lo ha
                                     # ancora fatto
  <vendor>: agreed | disagreed | inconclusive
    # "agreed": tutte le varianti del cluster hanno lo stesso verdetto per QUESTO vendor
    # "disagreed": non tutte concordano
    # "inconclusive": il cluster ha solo 2 varianti e discordano (nessuna maggioranza
    #   possibile con 2 campioni — esito onesto, non un difetto del processo)
```

**Precisazione terminologica** (trovata da `grill-with-docs`, non dal council — un
problema di ancoraggio del linguaggio, non di struttura): "verdetto" qui significa
sempre la classificazione binaria della metrica **primary** (`predicted_malicious` —
`metrics.py`, Gap 18), **mai** l'attribuzione di tecnica della metrica *strict*
(`technique_detected`). Motivo: `registro-limiti-aperti.md` registra che AlignmentCheck
(LlamaFirewall) "non produce un `technique_detected`... la colonna strict... resta
strutturalmente vuota (n/a)" — se `per_vendor_concordance` si ancorasse alla metrica
strict, sarebbe calcolabile solo per `aidr`, silenziosamente inutile per ogni vendor
senza attribuzione di tecnica. Ancorarlo alla primary (l'unica metrica comune a ogni
vendor per costruzione) evita esattamente la garanzia-valida-solo-per-un-vendor che il
principio 8 di `SPIRIT.md` vieta.

Questo resta metadato di autoria/interpretazione, mai letto da `schema.py`/`metrics.py`/
`Verdict` (stessa garanzia di `cases.yaml` oggi) — coerente con Nodo B. Il **dettaglio**
di come un vendor si è comportato su ciascuna variante (quale livello ha rotto il
pattern, perché) resta prosa in `vendor_scope_verification.yaml` al passo 5, dove
l'informazione narrativa appartiene per costruzione — `per_vendor_concordance` è solo
l'etichetta sintetica e verificabile, non sostituisce la prosa.

**Perché campi strutturati e non solo prosa nel `rationale`**: senza campi verificabili,
un'autoria futura (possibilmente delegata a un subagent) potrebbe generare una variante
in più o in meno, o registrare un accordo vendor sbagliato, senza che nessun controllo
automatico se ne accorga — la stessa classe di corruzione silenziosa che i principi 6/8
di `SPIRIT.md` vietano per il misuratore.

**Limite accettato, dichiarato esplicitamente** (trovato dal primo council-risk, punto
1, invariato in v4): il tracking resta auto-dichiarato per `variant_cluster_id`/
`variant_round_count` — un'entry che appartiene davvero a un cluster ma omette i campi è
indistinguibile da un caso singolo legittimo. Nessun controllo automatico chiude questa
scappatoia per costruzione. Accettato come limite (principio 3 `SPIRIT.md`), non risolto
qui.

**Nota sul valore della falsificazione pre-council** (invariata da v3): il prototipo
`temp/atlas-variant-stopping-prototype/` non ha mai eseguito un detector reale — i
verdetti erano inseriti a mano per esplorare la logica di stato (verificato leggendo il
README del prototipo). Valida la **terminazione** della regola `STRICT_3` per il caso a
3 livelli, non l'affidabilità di un verdetto di detector reale. Il caso a 2 livelli non
introduce stato adattivo, quindi non necessita di falsificazione propria.

## Passo 5 in dettaglio — `catalog/vendor_scope_verification.yaml`

Nuovo file (**non ancora committato — vedi nota sui test futuri sotto**), accanto a
`vendor_taxonomy_snapshot.yaml` (stesso pattern append-only di `cases.yaml`). Registra,
per ogni coppia vendor+tecnica (o vendor+meccanismo), cosa il vendor **dichiara** di
coprire contro cosa il meccanismo **verificato** fa davvero:

```yaml
entries:
  - vendor: aidr                          # o llamafirewall, o un vendor futuro
    technique_code: T0001                 # codice T00NN da vendor_taxonomy_snapshot.yaml,
                                           # o null se il finding non è legato a una
                                           # singola tecnica
    declared_scope: >
      <cosa il vendor dichiara di coprire — descrizione fedele, con citazione diretta
      quando esiste una fonte puntuale per quella tecnica; per un vendor senza
      tassonomia propria (es. LlamaFirewall), una sintesi verificabile del comportamento
      dichiarato a livello di prodotto, con la fonte primaria citata in evidence>
    verified_mechanism: >
      <cosa il meccanismo fa davvero, verificato leggendo il codice/prompt di sistema
      del vendor pinnato o osservando i verdetti reali. Se la fonte citata in evidence
      dichiara un limite statistico o un'asimmetria, riportare anche quello. Se questo
      cluster proviene dal passo 2, notare qui come QUESTO vendor si è comportato su
      ciascuna variante — coerente col valore di per_vendor_concordance per questo
      vendor in cases.yaml, mai in contraddizione con esso>
    verdict: in_scope | narrower_than_declared | out_of_scope
    evidence: >
      <path del research doc o del report che ha verificato questo — mai
      un'affermazione senza fonte. Verifica automatica: solo presenza del file su disco,
      non pertinenza del contenuto>
```

`verdict` a 3 valori: `in_scope` (il meccanismo copre quello che dichiara),
`narrower_than_declared` (dichiara un ambito ampio, il meccanismo ne copre solo una
parte), `out_of_scope` (il vendor non dichiara affatto di coprire quella tecnica).

**Limite dichiarato, non risolto qui** (convergenza 4/4 su tutti e tre i council):
append-only senza una policy di ri-verifica — un'entry resta silenziosamente valida
anche dopo che il vendor ha aggiornato il prodotto. Non risolto in questo documento —
resta un passo futuro esplicito (vedi Debito cumulativo sotto).

Due voci illustrative (invariate da v3, già verificate contro le fonti primarie):

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
      generalizzazione oltre questo run.
    verdict: narrower_than_declared
    evidence: docs/research/2026-08-26-analisi-metriche-intento-vs-effetto.md

  - vendor: llamafirewall
    technique_code: null
    declared_scope: >
      AlignmentCheck valuta se il comportamento dell'agente persegue l'obiettivo
      complessivo della sessione (goal hijacking) — ambito dichiarato ampio, a livello
      di sessione.
    verified_mechanism: >
      Verificato sul prompt di sistema reale e sulle rationale dei verdetti: il
      meccanismo valuta solo se l'azione corrente è coerente col messaggio utente
      immediatamente precedente — mai l'obiettivo complessivo o la sua legittimità.
      Asimmetria dichiarata esplicitamente dal research doc citato: il meccanismo è
      verosimilmente in ambito per un tipo di attacco diverso e non testato da questo
      dataset ("goal hijacking" come deviazione da un obiettivo legittimo originale)
      mentre è strutturalmente cieco proprio al pattern che questo dataset misura quasi
      esclusivamente: esecuzione compiacente di un'istruzione dannosa esplicita. Il
      verdict sotto si riferisce specificamente a questo secondo pattern.
    verdict: narrower_than_declared
    evidence: docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md
```

**Limite dichiarato** (invariato da v3): entrambe le voci hanno `technique_code: null`,
quindi il test "`technique_code` esiste nello snapshot" parte con zero copertura reale.

## Stato di implementazione (nuovo in v4)

**Trovato dal terzo council-risk, verificato da questa sessione**: nessuno dei file o
delle funzioni di test descritti in questo documento esiste ancora sul disco —
`catalog/vendor_scope_verification.yaml` non è committato, `tests/test_catalog.py` non
cita `variant_cluster_id`, `variant_round_count`, `per_vendor_concordance`, né alcun
check su `evidence`/`docs/**.md`. Il mapping Requisito→Verifica sotto descrive **cosa
verrà scritto nel primo piano di implementazione** (skill `writing-plans`, dopo
l'approvazione di questo documento), non lo stato attuale del repo — stesso status di
qualunque design doc di questo progetto prima del suo piano associato (es. Gap 18: vedi
`docs/design/2026-08-19-gap18-attack-succeeded-design.md`, che descriveva `criteria.py`
prima che esistesse). Dichiarato qui esplicitamente perché il terzo council ha trovato
che v3 non lo diceva, lasciando all'implicito una cosa facilmente esplicitabile.

## Falsificazione pre-council

Invariata da v3 nel merito (il prototipo non è stato rifatto). Vedi nota su cosa il
prototipo valida davvero, sopra (Passo 2).

| Assunzione | Esperimento | Risultato | Impatto sul design |
|---|---|---|---|
| `EARLY_STOP_2` (2 concordanti fermano subito, altrimenti fino a 2 in più) non si blocca mai | Testato il caso peggiore: detected, missed, poi ancora ambiguo a 3 varianti | Si blocca per davvero — serve una 4ª variante, ma solo 3 livelli di distanza superficiale sono mai stati definiti | Scartata |
| `STRICT_3` (sempre e solo 3 varianti, decidi lì) regge sempre | Testato convergente e divergente | Regge sempre, combacia coi 3 livelli | **Adottata** per il caso a 3 livelli — riletta come politica di autoria fissa (2 o 3 deciso dal criterio esplicito), con giudizio di concordanza per-vendor scritto in `per_vendor_concordance` + prosa (v4) |
| `MAJORITY_3` (2 concordanti fermano subito; altrimenti la 3ª decide per maggioranza) non si blocca mai | Testati entrambi i rami, confermata vera | Ma la regola decide se autorare la 3ª variante in base a un verdetto di detector, in tensione coi principi 1/2 `SPIRIT.md` (trovato indipendentemente da due council separati) | **Adottata in v1, scartata in v2/v3/v4** |

## Requisito → Verifica

**Stato**: nessuno dei test sotto esiste ancora — vedi "Stato di implementazione" sopra.

| Requisito | Verifica eseguibile (da scrivere) |
|---|---|
| Ogni entry di `catalog/vendor_scope_verification.yaml` ha tutti i campi obbligatori | `test_catalog.py`, nuova funzione mirror di `test_every_entry_has_all_required_fields` |
| `technique_code` (quando non `null`) esiste in `vendor_taxonomy_snapshot.yaml` | `test_catalog.py` — **copertura reale nulla finché una voce futura non valorizza il campo** (limite dichiarato) |
| `verdict` è uno dei 3 valori ammessi | `test_catalog.py` |
| `evidence` cita un path `docs/**.md` che esiste su disco (presenza, non pertinenza) | `test_catalog.py` |
| Entry di `cases.yaml` che condividono un `variant_cluster_id` sono in numero pari a `variant_round_count` ∈ {2, 3} | `test_catalog.py` |
| `per_vendor_concordance` (quando presente) usa solo i valori `agreed`/`disagreed`/`inconclusive`, e `inconclusive` compare solo quando `variant_round_count == 2` | `test_catalog.py` — nuova, sostituisce il test di omogeneità cross-cluster che il secondo council-risk aveva proposto per il vecchio `concordance` singolo (reso superfluo dalla struttura per-vendor, non dalla sua assenza) |
| Nessun modulo in `src/toy_agent` importa da `catalog/` | Verificato per costruzione, invariato: `dataset.py::load_dataset()` legge solo `*.yaml` dentro `dataset_dir`, mai `catalog/` |
| Nessun caso di test viene incluso, escluso, o classificato in modo vendor-neutro in base a un output di detector osservato durante l'autoria | **Non verificabile da un test automatico** — proprietà del processo e dello schema (nessun campo di concordanza vendor-neutro su `cases.yaml`), verificabile solo da revisione umana |

**Esito del mapping**: tre council indipendenti, su tre esecuzioni separate, hanno
contestato in modo sostanziale la stessa area del documento (passo 2) da angolazioni
diverse ogni volta — non un affinamento incrementale, una correzione di meccanismo
seguita da due correzioni di dettaglio reale. Il mapping stesso (non solo il meccanismo)
è stato corretto due volte (v2: aggiunte verifiche mancanti; v4: dichiarato lo stato
"da scrivere").

## Debito cumulativo, dichiarato esplicitamente (nuovo in v4)

**Trovato dal terzo council-risk**: attraverso tre revisioni si sono accumulati 4 limiti
"non risolti qui" — elencati qui in un solo posto invece che sparsi, con una decisione
esplicita di non aprirli ora:

1. **Nessuna policy di ri-verifica** per `vendor_scope_verification.yaml` (convergenza
   4/4 su tutti e tre i council).
2. **Nessuna integrazione in `report.py`** — un lettore del report pubblicato non
   distingue da solo un miss "fuori ambito dichiarato" da un miss reale (primo
   council-advocate, confermato dal terzo).
3. **Rischio di collisione di segnale** (T0005/T0010, T0002/T0012 già registrati in
   `registro-limiti-aperti.md`) che il metodo a 2-3 varianti può aumentare attivamente,
   non solo ereditare (primo council-risk).
4. **Copertura zero del test `technique_code`** finché entrambe le voci illustrative
   restano `technique_code: null` (secondo/terzo council-advocate).

**Decisione esplicita**: nessuno dei quattro viene aperto in questo documento. Non è un
rinvio implicito — è una scelta consapevole di scope, motivata dal fatto che tutti e
quattro sono task a sé (integrazione UI/report, policy operativa, revisione
sistematica del dataset esistente, popolamento del catalogo), meglio affrontati come
piani dedicati quando il research doc (Nodo A) genera lavoro reale su di essi, non
come parte del meccanismo che questo documento fissa.

## Cosa NON cambia

- `schema.py`, `metrics.py`, `Verdict` — nessuna modifica. **Verificato contro il
  criterio esatto, non contro un elenco** (trovato da `grill-with-docs`): il principio 6
  di `SPIRIT.md` definisce il "misuratore" per criterio — "ogni componente che produce,
  giudica o verifica il numero pubblicato" — non per elenco di moduli (la stessa
  correzione fu fatta in passato in questo progetto proprio su questo principio, vedi
  memoria `project_spirit_misuratore_per_criterio`). `catalog/vendor_scope_verification.yaml`
  e i nuovi campi di `cases.yaml` non producono, giudicano, né verificano P/R/F1 — sono
  letti da un analista in fase di interpretazione, mai da `metrics.py` — quindi restano
  fuori dal misuratore per lo stesso criterio, non per un'esenzione ad hoc.
- La regola del "gemello benigno" per ogni tecnica — invariata.
- Nessun campo booleano `in_declared_scope` su `Verdict` o su `TestCase`.

## Esplicitamente fuori scope da questo design

- Il cross-check completo T0001-T0014 vs MITRE ATLAS — research doc separato (Nodo A),
  che deve definire il criterio di mappabilità tecnica ATLAS→tool come suo primo passo.
- Il popolamento reale di `vendor_scope_verification.yaml` oltre le due voci
  illustrative.
- Qualunque estensione futura del Nodo D.
- T0009/T0011 (Gap 17).
- I 4 punti della sezione "Debito cumulativo" sopra.
