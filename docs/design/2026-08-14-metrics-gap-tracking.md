# Gap tracking: metrics + report (Plan 2)

Companion di `docs/superpowers/plans/2026-08-14-metrics-and-report.md`. Ogni gap
trovato durante il council checkpoint su Plan 2 va registrato qui con stato,
evidenza e risoluzione, prima di essere eventualmente riportato nel piano stesso.

Stati possibili: `open`, `in discussione`, `risolto nel piano`, `accettato come limite dichiarato`.

## Council checkpoint su Plan 2 — esecuzione

Eseguito il 2026-08-14, roster completo (`council-skeptic`, `council-risk`,
`council-pragmatist`, `council-advocate`), ognuno con il piano di implementazione
completo, il design doc (`2026-08-14-toy-agent-e-pipeline-misura.md`) e il
gap-tracking doc di Plan 1 (`2026-08-14-toy-agent-gap-tracking.md`) come contesto.

## Gap 8 — Report mancante di estratto del transcript nei casi concreti

**Stato**: risolto nel piano.

**Trovato da**: council-skeptic + council-advocate (indipendentemente).

**Severità**: maggiore — tocca la leggibilità del report per il lettore target.

**Evidenza**: il design doc (sezione "Report", parte 4) dice esplicitamente:
"almeno 2-3 esempi reali di `TestCase` che il detector ha sbagliato (falso
negativo o falso positivo), con estratto del transcript e della rationale —
non solo il numero aggregato, un lettore deve poter vedere *cosa* è stato
mancato." Il piano di Plan 2 (`_find_misclassified_cases` + sezione "Concrete
Cases" di `render_report`) mostra `case_id`, `label`, `technique_target`,
`rationale` — ma **mai il transcript**. Un lettore non può vedere cosa il
detector ha effettivamente processato.

**Risoluzione applicata**: `render_report` ora include un estratto del
`Transcript` per ogni caso sbagliato — i primi N turni (default 3) del
`Transcript.turns`, formattati come `role: content` (troncati se troppo
lunghi). Aggiunto al piano: Task 3, sezione "Concrete Cases".

## Gap 9 — Per-technique precision è sempre 1.0 per costruzione

**Stato**: risolto nel piano.

**Trovato da**: council-skeptic + council-pragmatist (indipendentemente).

**Severità**: moderata — non tocca la validità della misura primaria, ma
produce un numero fuorviante nel report.

**Evidenza**: il breakdown per `technique_target` traccia solo `tp` e `fn`
(fp/tn non si applicano: `technique_target` è definito solo per casi malevoli,
quindi un falso positivo non ha una tecnica target a cui associarsi). Ma
`_compute_scores` calcola comunque `precision = tp / (tp + fp)` con `fp=0`,
che restituisce sempre `1.0` (o `0.0` se `tp=0`). Un lettore che vede
"T0001: Precision=1.000" potrebbe leggere "il detector è perfetto per questa
tecnica" quando in realtà significa solo "non contiamo falsi positivi per
tecnica". È esattamente il tipo di numero fuorviante che `SPIRIT.md` contesta
ai benchmark dei vendor.

**Risoluzione applicata**: il per-technique breakdown ora riporta solo
`tp`, `fn`, `recall` e `recall_ci` — non `precision`/`f1` (che sarebbero
fuorivianti con `fp=0` per costruzione). Il tipo `MetricScores` resta
invariato (è usato per le metriche primaria/strict dove fp/tn sono
significativi), ma il per-technique dict usa un tipo più snello
`TechniqueBreakdown(tp: int, fn: int, recall: float, recall_ci:
ConfidenceInterval)` che espone solo i campi significativi. Aggiunto al
piano: Task 1 (nuovo tipo) + Task 2 (per_technique usa il nuovo tipo).

## Gap 10 — Duplicate case_id nei verdicts silenziosamente sovrascritti

**Stato**: risolto nel piano.

**Trovato da**: council-skeptic.

**Severità**: minore — non tocca la validità della misura, ma può causare
una silenziosa perdita di dati.

**Evidenza**: `compute_metrics` costruisce `verdict_map: dict[str, Verdict]`
iterando sui verdicts. Se due verdicts hanno lo stesso `case_id`, il secondo
sovrascrive silenziosamente il primo. Il piano verifica `case_id` mancanti
ma non duplicati.

**Risoluzione applicata**: `compute_metrics` ora rileva `case_id` duplicati
nei verdicts e solleva `ValueError`. Aggiunto al piano: Task 2, test
`test_compute_metrics_duplicate_verdict_raises`.

## Gap 11 — Report senza timestamp, design doc dice "a parte timestamp"

**Stato**: accettato come limite dichiarato (deviazione consapevole dal design doc).

**Trovato da**: council-pragmatist.

**Severità**: minore — il design doc dice "rigenerare il report dagli stessi
`TestCase`/`Verdict` produce un file identico (bit a bit, a parte timestamp)".
Il piano non include un timestamp nel report, rendendolo **completamente**
deterministico (non "a parte timestamp"). Questo è in realtà *migliore* per
la riproducibilità (principio 4, `SPIRIT.md`): un report senza timestamp è
verificabile bit a bit, non "bit a bit tranne una parte che cambia sempre".

**Risoluzione**: nessuna modifica al piano. La deviazione è consapevole e
migliora il requisito. Il report resta senza timestamp. Da documentare nel
report finale (sezione Methodology) se necessario.

## Gap 12 — Test fragili per error_count e vendor comparison

**Stato**: risolto nel piano.

**Trovato da**: council-skeptic.

**Severità**: minore — i test passano oggi ma potrebbero passare per il
motivo sbagliato.

**Evidenza**: `test_report_contains_error_count` usa `assert "1" in report` —
la stringa "1" appare in molti punti (numeri di sezione, "1.0", ecc.).
`test_report_includes_vendor_comparison` usa `assert "1.0" in report` —
"1.0" appare in precision/recall quando sono perfetti. Entrambi i test
passerebbero anche se la funzionalità fosse rotta.

**Risoluzione applicata**: i test ora cercano stringhe più specifiche.
`test_report_contains_error_count` cerca `"Detector errors (status=error): 1"`.
`test_report_includes_vendor_comparison` cerca `"P=1.0, R=0.667"`. Aggiornato
nel piano: Task 3.

## Gap 13 — Per-technique recall usava la definizione primaria (label-only), non strict

**Stato**: risolto (whole-branch review del secondo revisore, post-esecuzione).

**Trovato da**: audit indipendente del branch eseguito da un secondo modello
(Claude Sonnet 5), richiesto esplicitamente dall'utente perché il piano era
stato eseguito da un altro modello (Claude Sonnet 4 via Cline).

**Severità**: maggiore — produce un numero fuorviante esattamente nel punto del
report che dovrebbe mostrare la qualità di attribuzione per tecnica specifica,
la stessa famiglia di problema di Gap 9 (numero tecnicamente corretto ma letto
in modo sbagliato da chi legge il report).

**Evidenza**: in `compute_metrics` (`metrics.py`), il ciclo che popola
`per_tech[tech]` contava come `tp` qualunque caso `actual_malicious and
predicted_malicious`, senza verificare `v.technique_detected ==
case.technique_target` — cioè usava la definizione della metrica *primaria*
(label-only), non quella *strict* (attribuzione tecnica), pur essendo l'unico
punto del report dove il lettore vede un numero legato a una tecnica
specifica. Verificato empiricamente: un detector che classifica correttamente
ogni caso T0001 come `malicious` ma attribuisce sempre la tecnica sbagliata
(sempre T0009) produce `strict.tp=0`/`strict.fn=3` (corretto) ma
`per_technique["T0001"].recall=1.0` (fuorviante) — contraddizione diretta
nello stesso report tra la sezione "strict metric" e il breakdown per
tecnica.

**Risoluzione applicata**: il conteggio per-tecnica ora richiede lo stesso
match di tecnica della metrica strict (`v.technique_detected ==
case.technique_target` per contare `tp`, altrimenti `fn`). Aggiunto test di
regressione `test_compute_metrics_per_technique_recall_requires_technique_match`
in `tests/toy_agent/test_metrics.py` (scritto per fallire sul codice
originale, verificato che fallisse, poi la correzione l'ha fatto passare).

**Estensione (stessa correzione, testo originale del design doc)**: rileggendo
il testo originale della sezione "Modulo metriche" (non la parafrasi del
piano) durante `finishing-a-development-branch` — "Entrambe [le due metriche]
con intervallo di confidenza esplicito e breakdown per technique_target" — il
requisito chiede un breakdown per tecnica per **entrambe** le metriche
(primaria e strict), non una sola tabella. Aggiunto un secondo campo
`MetricsResult.per_technique_primary` (label-only, indipendente
dall'attribuzione) accanto a `per_technique` (rinominato concettualmente a
"strict" ma non nel nome del campo, per non rompere i consumer esistenti).
Il report ora mostra entrambe le tabelle, con header distinti ("strict —
technique-attribution recall" / "primary — detection recall,
technique-agnostic"). Nuovi test:
`test_compute_metrics_per_technique_recall_requires_technique_match`
(esteso) e `test_report_contains_both_per_technique_breakdowns`.

## Esito council checkpoint

- `council-skeptic`: d'accordo con riserve. Ha trovato Gap 8 (transcript
  mancante), Gap 9 (per-technique precision fuorviante), Gap 10 (duplicate
  case_id), Gap 12 (test fragili) — tutti risolti nel piano.
- `council-risk`: rischio basso. Nessun gap di sicurezza o validità della
  misura trovato oltre a quelli già coperti dal design doc. L'F1 CI
  approssimato (corners method) è conservativo e dichiarato — accettabile.
- `council-pragmatist`: dimensionato correttamente. Ha notato Gap 11
  (timestamp) — accettato come deviazione consapevole, non richiede modifica.
  Ha confermato che Wilson CI con z-values hardcoded (no scipy) è la scelta
  pragmatica corretta.
- `council-advocate`: ha spigoli grezzi. Ha trovato Gap 8 (transcript
  mancante) indipendentemente da council-skeptic — un lettore deve poter
  vedere *cosa* è stato mancato, non solo *che* è stato mancato. Risolto.

**Esito mapping Requisito→Verifica**: tutte le verifiche del design doc
applicabili a Plan 2 sono coperte dai test del piano. Nessuna verifica
esistente è stata contestata. Il council ha aggiunto 4 gap nuovi (8-12),
non corretto verifiche esistenti.

## grill-with-docs — esecuzione

Eseguito il 2026-08-14, incrociando il piano di Plan 2 con `SPIRIT.md` e il
design doc (`2026-08-14-toy-agent-e-pipeline-misura.md`) per intero.

Nessun punto di precisione trovato che richieda correzione. Verifiche chiave:

- Design doc: "20-30 casi per label (40-60 totali)" → piano Global Constraints:
  "20-30 casi per label, 40-60 totali" — coerente.
- Design doc: "confronto diretto fianco a fianco con i numeri dichiarati dal
  vendor (P=1.0, R=0.667)" → piano Executive Summary + test `P=1.0, R=0.667`
  — coerente.
- Design doc: "almeno 2-3 esempi reali" → piano `limit=3` in
  `_find_misclassified_cases` — coerente.
- Design doc: 5 parti del report → piano ha tutte e 5 — coerente.
- Design doc: "Non importa mai né AgentEvent né altri tipi specifici del
  tool sotto test" → piano `metrics.py` importa solo da `.schema` — coerente.
- SPIRIT.md principio 3: "dichiarare esplicitamente intervalli di confidenza
  o limiti di generalizzabilità" → piano lo fa in Methodology section —
  coerente.
- Design doc: "cost_usd ... il modulo metriche deve calcolarlo a partire da
  token count + pricing" → questo è responsabilità di Plan 4 (adapter), non
  di Plan 2 (metrics). Il modulo metriche non usa `cost_usd` nei TP/FP/FN/TN
  — coerente, non è una mancanza.

Nessuna correzione necessaria. Il piano è pronto per l'implementazione.
