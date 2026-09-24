# Audit effetti ↔ etichette sui transcript pubblicati (2026-09-24)

Script usa-e-getta, in sola lettura, che hanno prodotto le evidenze del Gap 22 e del Gap 23
(`docs/design/2026-08-14-toy-agent-gap-tracking.md`). Leggono `dataset/`, `src/toy_agent/`
e `docs/reports/*/` e non scrivono niente. Si possono lanciare da qualunque cartella:
`python docs/research/2026-09-24-audit-effetti-transcript/<script>.py`.

Non sono test e non sono lo strumento ufficiale di calcolo delle metriche. Il Gap 23 propone
di trasformare `effect_audit.py` in un test.

| Script | Cosa fa | Usato per |
|---|---|---|
| `effect_audit.py` | Per ogni coppia run-caso ricava gli effetti dalle chiamate riuscite (backdoor, dati di altri clienti, ticket altrui, email esterne, modifiche all'account) e li mette accanto a `label` e `attack_success_criteria`. Stampa quattro gruppi di sospetti da rileggere a mano | Gap 23 |
| `tool_errors.py` | Elenca ogni chiamata fallita di tutti i run, raggruppata per tool e messaggio d'errore | Gap 22, tabella dei tool |
| `malicious_matrix.py` | Per ogni caso malevolo e ogni run: esito del criterio, sequenza di chiamate (✓/✗) e inizio della risposta finale | Gap 22, classificazione manuale dei 49 fallimenti |
| `interpretation_key.py` | Applica la chiave di lettura meccanica (`docs/design/2026-09-24-chiave-di-lettura-verdetti.md`, sezione 5) a tutti i run: esito di riferimento per coppia run-caso, metrica per effetto, casi `always` separati, non giudicabili. La confronta con la classificazione manuale di `artifact_metrics.py` | Chiave di lettura, sezione 5 |
| `artifact_metrics.py` | Ricalcola precision e recall con la logica di `metrics.py`, trattando le coppie artefatto come esito sconosciuto e applicando le correzioni del Gap 23 (punti 1 e 5) | Gap 22, tabella delle metriche |

**Limite da tenere presente**: in `artifact_metrics.py` la classificazione degli artefatti
(dizionario `ART`) è scritta a mano, a partire dall'output di `malicious_matrix.py`. La
regola meccanica che la sostituisce sta in `interpretation_key.py`, e diverge dalla
classificazione manuale in 2 coppie su 138 (vedi la chiave di lettura, sezione 5).
