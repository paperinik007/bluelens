# Deviazione dichiarata da "nessuna modifica a metrics.py" per gestire target synthetic

**Status**: Accepted (2026-08-30)

## Context

Il design v4 (`docs/design/2026-08-30-atlas-audit-method-design-v4.md`, sezione "Cosa
NON cambia", riga 395) dichiara: "schema.py, metrics.py, Verdict — nessuna modifica",
motivato dal principio 6 di SPIRIT.md (il misuratore è definito per criterio — ogni
componente che produce, giudica o verifica il numero pubblicato — non per elenco). Lo
spec per il popolamento dei 6 gap ATLAS
(`docs/design/2026-08-30-atlas-6-gap-spec.md`, decisione in
[ADR-0001](./0001-synthetic-technique-target-atlas-gaps.md)) introduce `technique_target`
sintetici (`T-ATLAS-{variant_cluster_id}`) per tecniche senza T-code vendor. Questi
target non corrisponderanno mai a un `technique_detected` reale di alcun vendor, quindi
un breakdown strict per-tecnica invariato produrrebbe un FN garantito per costruzione —
non un segnale reale sulla qualità del detector, ma un artefatto di labeling pubblicato
come se fosse un dato.

## Decision

Estendere `TestCase` con `strict_significant: bool = True` (default sicuro,
backward-compatible) ed estendere `metrics.py` per escludere i casi con
`strict_significant: False` dal breakdown strict per-tecnica (`per_tech_strict`),
mantenendoli nella metrica primary (`per_tech_primary`). Questa è una **deviazione
dichiarata** dalla lettera di "nessuna modifica" del design v4, non un'eccezione
implicita giustificata da "è solo additiva" — il criterio del design v4 lega il
vincolo al ruolo del file (produce/giudica/verifica il numero pubblicato), non alla
dimensione della modifica. La deviazione è giustificata dal principio 8 di SPIRIT.md
(strutturale prima di contingente): lasciare `metrics.py` invariato lascerebbe un FN
garantito per costruzione dentro un numero pubblicato — la patch rende la garanzia
strutturale, non dipendente da un'osservazione contingente.

## Consequences

- `metrics.py` non è più "invariato" dal design v4 in senso letterale — un futuro
  audit dei vincoli del design v4 deve sapere che questa deviazione esiste e perché.
- Il precedente vale per casi futuri analoghi (nuovi target sintetici, nuovi vendor
  senza `technique_detected`): l'esclusione dal breakdown strict via
  `strict_significant: False` è ora il pattern stabilito, non va reinventato.
- Nessun impatto sulla metrica primary, che resta l'unica metrica realmente comune a
  ogni vendor (stesso principio già applicato a LlamaFirewall/`per_vendor_concordance`).

## Alternatives considered

- **Lasciare la citazione del design v4 come "nessuna modifica sostanziale"** (versione
  precedente di questa spec): scartata perché la parola "sostanziale" non è nel testo
  originale — citarla come vincolante avrebbe nascosto la deviazione reale invece di
  dichiararla.
- **Non toccare `metrics.py` per niente, accettare il breakdown strict distorto**:
  scartata perché viola direttamente il principio 8 — pubblicherebbe un numero (FN sui
  casi synthetic) che non è un segnale strutturale ma un artefatto.
