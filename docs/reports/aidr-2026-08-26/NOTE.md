# Nota di pubblicazione

Questo report **non sostituisce** `docs/reports/agentic-threat-detection-2026-08-19/`
nel senso di cancellarlo — entrambi restano pubblicati per intero (principio 4/7,
`SPIRIT.md`: risultati grezzi pubblicati, nessun run scompare dalla storia). Ma è la
misura più aggiornata e corretta: eseguito il 2026-08-26 con codice del misuratore
successivo alla chiusura di Gap 19/20/21 (`measurer_commit=da886e0`, vs. il commit
precedente usato per il report del 19/08, che soffriva del bug Gap 19: argomenti di
tool call malformati assorbiti silenziosamente invece di essere esclusi dalla misura).

**Confronto numerico** (primary, label-only):

| | 08-19 (pre-Gap19) | 08-26 (post-Gap19/20/21) |
|---|---|---|
| Precision | 0.250 [0.046, 0.699] | 0.200 [0.036, 0.624] |
| Recall | 0.250 [0.046, 0.699] | 0.333 [0.061, 0.792] |
| F1 | 0.250 | 0.250 |
| TP/FP/FN/TN | 1/3/3/24 | 1/4/2/24 |

Strict (technique attribution): 0.000 in entrambi. La differenza numerica è coerente
con la normale variabilità di campionamento del modello (stesso ordine di grandezza,
CI ampiamente sovrapposti) — non un effetto del fix. Il fix di Gap 19 non ha trovato
nessun caso reale in cui un argomento malformato fosse stato eseguito silenziosamente
in questo run (0/44 tool call con argomenti non-dict o illeggibili); la ragione di
pubblicare comunque questo run è che è la prima misura eseguita **su codice già
corretto**, non perché il numero precedente fosse sbagliato.

Un run intermedio (2026-08-21, pre-fix, stessa dimensione) era stato eseguito e poi
deliberatamente non pubblicato in attesa della chiusura di Gap 19 — non recuperato:
questo run del 08-26, eseguito dopo il fix, lo rende superfluo.

Provenienza completa, per-caso: `provenance.json`, `run.log`, `verdicts.jsonl` in
questa stessa directory.
