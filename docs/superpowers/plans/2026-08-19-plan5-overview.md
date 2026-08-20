# Plan 5 — panoramica dei 4 piani di implementazione

> Gap 18 resolved in code, see
> `docs/design/2026-08-19-gap18-attack-succeeded-design.md` and
> `docs/superpowers/plans/2026-08-19-gap18-attack-succeeded-implementation.md`.

Indice, non contenuto: il lavoro residuo di Plan 5 (dataset di audit, design doc
`docs/design/2026-08-19-plan5-dataset-design.md`) è strutturato in 4 piani separati
invece di uno solo, per rispettare lo Scope Check di `superpowers:writing-plans`
(sottosistemi indipendenti, ciascuno capace di produrre qualcosa di verificabile da
solo) — deciso con l'utente il 2026-08-19. Questa pagina esiste solo per tenere la
visione di insieme mentre si esegue un piano a sessione: non ripete il contenuto dei
singoli piani, punta lì.

## I 4 piani, in ordine di dipendenza

1. **[5a — Catalogo](2026-08-19-plan5a-catalog-completion.md)** — completa
   `catalog/cases.yaml` (T0007 nuovo scenario + codice, tecniche restanti, gemelli
   benigni, benigni generici) e il cross-check di copertura contro le tassonomie
   esterne. Nessuna dipendenza dagli altri 3.
2. **[5b — Gate di verifica](2026-08-19-plan5b-verification-gates.md)** — le 4
   verifiche ancora assenti (coverage gate, anti-scorciatoia tool→label, coerenza
   catalogo↔dataset, validazione template). Solo codice, nessun contenuto di
   catalogo/dataset — **indipendente da 5a**, si può eseguire in parallelo o prima.
3. **[5c — Dataset](2026-08-19-plan5c-dataset-authoring.md)** — scrive i `TestCase`
   YAML reali in `dataset/` selezionando dal catalogo. **Dipende da 5a** (il catalogo
   deve essere completo prima di selezionare da esso — o almeno le voci di cui questo
   piano scrive i `TestCase` devono già esistere come `candidate` in `catalog/cases.yaml`).
4. **[5d — Integrazione finale](2026-08-19-plan5d-integration.md)** — aggiorna
   `README.md`, esegue `run_batch.py` sul dataset completo, produce il primo report
   reale. **Dipende da 5b e 5c entrambi completi** (il gate di copertura e
   l'anti-scorciatoia devono esistere prima che l'esecuzione completa sia permessa;
   il dataset deve esistere per avere qualcosa da eseguire).

```
5a (catalogo) ──┐
                ├─→ 5c (dataset) ─┐
5b (gate)  ─────┼─────────────────┼─→ 5d (integrazione)
                └─────────────────┘
```

5a e 5b non hanno dipendenze reciproche e possono essere eseguiti in qualunque ordine
o intrecciati sessione per sessione — non serve finire l'uno prima di iniziare l'altro.

## Decisioni di design prese durante la scrittura di questi piani (non ripetute nei piani stessi)

- **T0007 (Guardrail Evasion)**: nessun guardrail esisteva nel nostro mondo prima di
  questa sessione — aggiunta una clausola statica a `_SYSTEM_PROMPT`
  (`agent_loop.py`), identica su ogni caso (Gap 1-safe). Design approvato
  dall'utente 2026-08-19, con due correzioni (enumerare esplicitamente i 3
  `customer_id` nel ticket malevolo; `case_id` finale non deve ripetere il nome della
  tecnica). Dettaglio: Gap 16, `docs/design/2026-08-14-toy-agent-gap-tracking.md`;
  implementazione: Plan 5a Task 1.
- **T0009/T0011 (Covert Data Over-Collection, Tool-Result Tampering)**: nessuno
  scenario valido trovato senza rischiare di contaminare i casi benigni che
  condividono lo stesso tool (`query_customer_db`, il più usato del dataset).
  Accettato come limite dichiarato con l'utente 2026-08-19 — copertura minima di
  questo primo giro: **12/14 tecniche**, non 14/14. Analisi completa dei 4 meccanismi
  considerati e scartati (per non doverla rifare): Gap 17,
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`. Conseguenza propagata a: Plan
  5a (nessun task per T0009/T0011), Plan 5b (il coverage gate verifica 12 codici, non
  14), Plan 5d (il report finale dichiara l'eccezione).
- **Conteggio target del dataset corretto**: 16 malevoli minimo (non 18) + 12
  gemelli benigni minimo (non 14) + N generici, dopo l'esclusione di T0009/T0011 —
  vedi design doc, sezione "Regola di copertura minima" (corretta 2026-08-19).

## Stato di avanzamento (da aggiornare mano a mano che i piani vengono eseguiti)

- [ ] Plan 5a — non iniziato
- [ ] Plan 5b — non iniziato
- [ ] Plan 5c — non iniziato
- [ ] Plan 5d — non iniziato
