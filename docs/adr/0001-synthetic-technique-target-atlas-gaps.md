# Synthetic technique_target per i gap ATLAS senza T-code vendor

**Status**: Accepted (2026-08-30)

## Context

Il cross-check ATLAS (`docs/research/2026-08-30-atlas-taxonomy-crosscheck.md`) ha
identificato 6 tecniche ATLAS mappabili senza un T-code aidr corrispondente. Per
eseguirle come `TestCase` reali contro aidr serve un `technique_target`
(`schema.py:130` impone che un `TestCase` malicious lo dichiari, non-null) — ma
nessun T-code vendor esiste per queste tecniche, e il commento in testa a
`catalog/cases.yaml` riserva `technique_code: null` alle sole aree di comportamento
legittimo (benigno), non a tecniche malicious senza codice — le 3 entry esistenti con
`null` sono tutte `label_hint: benign`, zero precedenti per malicious.

## Decision

`technique_target` diventa `f"T-ATLAS-{variant_cluster_id}"` per questi casi (es.
`T-ATLAS-atlas-t0077-rendering`) — un ID sintetico per cluster di variante, non per
singolo codice ATLAS. `variant_cluster_id` è obbligatorio per le nuove entry di questo
batch in `cases.yaml` (resta opzionale/`null` per le 31 esistenti). Il campo
`strict_significant: bool = True` su `TestCase` (default `True`, `False` per questi
casi) esclude questi target sintetici dal breakdown strict per-tecnica in
`metrics.py`, restando visibili solo nella metrica primary — stesso trattamento già
riservato a LlamaFirewall (nessun `technique_detected`).

## Consequences

- `technique_target` ha ora significato overloaded: T-code vendor reale
  (`T0001`-`T0014`) per casi normali, ID di cluster ATLAS per casi synthetic.
  `metrics.py` lo tratta sempre come stringa opaca, ma un lettore futuro deve sapere
  che i due significati coesistono.
- Confronto diretto nel test bridge
  (`case.technique_target == f"T-ATLAS-{entry.variant_cluster_id}"`), nessuna
  manipolazione di stringhe — funziona identico per gap singoli e accoppiati (dove
  `atlas_codes` è una lista di 2 elementi).
- Un breakdown strict per-tecnica pubblicato su questi target sarebbe un FN garantito
  per costruzione (aidr non riporterà mai `technique_detected == "T-ATLAS-..."`) —
  `strict_significant: False` rende questa garanzia strutturale (principio 8,
  `SPIRIT.md`), non un'omissione manuale.

## Alternatives considered

- **`technique_target = "T-ATLAS-T####"` con suffisso `AML` e confronto per rimozione
  di prefisso**: scartata per due motivi strutturali — le coppie (AML.T0006+AML.T0084,
  AML.T0103+AML.T0108) hanno `atlas_codes` come lista di 2 elementi mentre
  `technique_target` è singolo, quindi nessun codice della coppia è "il" target da
  solo; e il confronto proposto aveva un bug concreto
  (`"T-ATLAS-T0077".removeprefix("T-ATLAS-")` = `"T0077"`, mai presente in
  `["AML.T0077"]`).
- **Le 6 categorie restano `status: candidate` per sempre, mai eseguite**: scartata
  perché elimina ogni verdetto empirico da aidr per i 6 gap — in tensione con
  l'obiettivo dichiarato del batch (popolare `vendor_scope_verification.yaml` col
  Passo 5 del metodo, che richiede un meccanismo verificato, non solo prosa).
- **Modifica a `schema.py` per permettere `technique_target: null` su `TestCase`
  malicious quando è valorizzato un codice ATLAS**: scartata perché contraddice
  esplicitamente "Cosa NON cambia: schema.py" del design v4.
- **Campo `cluster_id` separato su `TestCase`, distinto da `technique_target`**:
  scartata per evitare due campi paralleli con la stessa cardinalità informativa — il
  sovraccarico semantico di un solo campo (`technique_target`) è preferito alla
  ridondanza di due.
