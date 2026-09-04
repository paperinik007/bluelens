# R10 — Output del preflight non sanitizzato a valle del tipo di ritorno

Data: 2026-08-26. Stato: **risolto nel codice (fix test-only, nessun cambio di contratto)**.
Riferita da `docs/design/registro-limiti-aperti.md`, voce "`run_batch.main()` si fida
ciecamente dell'output di `preflight_check_models`".

## 0. Conclusione (letta prima di tutto)

Il codice sorgente sanitizza già correttamente (`_probe()` restituisce solo
`exc.__class__.__name__` o status code HTTP). Il difetto non era nel codice: era nel
**test**, che aggirava il percorso reale (fake che *solleva* invece di *ritornare*). Il
fix è **solo il test**: un test end-to-end che esercita il preflight reale con un
`httpx.MockTransport` che solleva un'eccezione contenente un sentinel, e verifica che il
sentinel non raggiunga `run.log` mentre la classe dell'eccezione sì.

L'ipotesi del dataclass `PreflightFailure` (sezione 4 originale) è stata **scartata**: un
tipo strutturato non obbliga nulla — è una convenzione più esplicita, non un filtro. Chi
scriverà il prossimo `except` può comunque fare `str(exc)`. L'unico obbligo reale in
questo progetto è la **suite di test** (verde prima di ogni commit): un test sentinella
fallisce il commit se il raw text rientra, qualunque sia la forma del tipo di ritorno.

## 1. Il problema

In `src/toy_agent/run_batch.py` (righe ~302-305):

```python
preflight_failures = preflight_check_models(os.environ, api_key, agent_api_key=agent_api_key)
if preflight_failures:
    for failure in preflight_failures:
        progress(f"preflight model check failed: {failure}")
```

`preflight_check_models` restituisce `list[str]` — stringhe **già sanificate oggi**, ma
il tipo non lo garantisce. La disciplina del progetto ("nessun messaggio raw di eccezione
raggiunge output", perché può contenere la API key) è rispettata **solo per contingenza
del preflight**, non per costruzione nel punto di stampa. Se in futuro una nuova causa di
fallimento restituisse testo libero (es. il messaggio di un'eccezione), quel testo
finirebbe in `run.log` e su stderr senza alcun filtro.

È esattamente il difetto che `SPIRIT.md` principio 8 vieta: una garanzia che vale solo
perché *oggi*, per *questo* codice, sembra vera — non per l'interfaccia dichiarata.

## 2. Perché oggi il rischio è latente, non attivo

`src/toy_agent/preflight.py`, `_probe()`:

```python
except httpx.HTTPStatusError as exc:
    return f"{tier} ({model}): HTTP {exc.response.status_code}"
except Exception as exc:
    return f"{tier} ({model}): {exc.__class__.__name__}"
```

Le uniche due cause producono status code HTTP o `__class__.__name__` — mai il testo
dell'eccezione. E `preflight_check_models` aggiunge solo il literal
`"agent ({model}): AGENT_OPENROUTER_API_KEY is not set"`. Quindi il vincolo è oggi
rispettato.

Il test R10 (`tests/toy_agent/test_run_batch.py::test_preflight_sentinel_exception_text_never_reaches_run_log`)
lo aggira: il fake **solleva** `RuntimeError(sentinel)` invece di **ritornare** una
stringa. Un fake che ritornasse una stringa con testo sentinella fallirebbe — il che
espone la mancanza di un filtro a monte, non la verifica.

## 3. Perché un filtro su stringhe non funziona

La soluzione "sanitizzare in `main()` prima di passare a `progress()`" (abbozzata nel
registro) non è implementabile in modo affidabile: non esiste un modo per distinguere
"testo raw da eccezione" da "testo legittimo" operando su una stringa opaca. Qualunque
filtro per pattern è aggirabile e reintroduce il difetto per omissione.

## 4. La soluzione (corretta): il test sentinella end-to-end, non un nuovo tipo

> **Questa sezione sostituisce la versione originale, che proponeva un dataclass
> `PreflightFailure`. Quella proposta è stata scartata come falsa sicurezza — vedi
> sezione 0.**

Il gap si chiude rendendo *verificabile automaticamente* la sanificazione, non cambiando
il contratto. Il test end-to-end (`tests/toy_agent/test_run_batch.py`,
`test_preflight_sentinel_exception_text_never_reaches_run_log`) fa questo:

- imposta `SIFTER_MODEL` così il preflight reale esegue davvero la probe sul tier;
- inietta un `httpx.MockTransport` il cui handler solleva `Boom("Authorization: Bearer sk-SENTINEL-not-a-real-key")`;
- invoca `main()` con il **preflight reale** (non un fake che aggira);
- asserisce che `run.log` **non** contenga il sentinel, ma contenga `Boom` (la classe) e
  `preflight model check failed` (il fallimento è registrato, non silenziato).

Perché questo è l'unico obbligo reale: è l'unica cosa che *esegue e fallisce* — se in
futuro qualcuno cambia `_probe()` in `return f"...: {str(exc)}"`, la suite fallisce e il
commit è bloccato. Non dipende dalla memoria né dalla disciplina di chi scrive il
`except` successivo.

### 4.1 Cosa NON fa (limite onesto)

Il test copre il percorso reale *oggi* esistente (l'eccezione in `_probe()`). Se un
futuro sviluppatore aggiungesse una **nuova** causa di fallimento che ritorna testo raw
in un ramo non esercitato dal test, il test non lo coglierebbe finché quel ramo non viene
attraversato. Nessun meccanismo Python può rendere il leak *impossibile* (a differenza del
confine `agent`/`detector` in Docker, che è fisico). La garanzia ottenuta è: *qualunque
violazione nel percorso testato blocca il commit*, che è la garanzia più forte che questo
progetto abbia scelto come standard per il codice.

## 5. Impatto effettivo (fix test-only)

| File | Modifica |
|---|---|
| `tests/toy_agent/test_run_batch.py` | `import httpx` + `from toy_agent import preflight`; riscrittura del test R10 in end-to-end |
| *(nessun file sorgente)* | — |

Criteri di tiering: nessun `schema.py`, nessun
confine, nessun nuovo design doc, nessun cambio di comportamento visibile → **Micro**.
La modifica è un test che rafforza la copertura, non un cambio di codice di produzione.

## 6. Stato

- **Risolto** (2026-08-26): test R10 end-to-end committato, suite `459 passed, 2 skipped`.
- **Riattivazione futura (se serve)**: se emergerà una nuova causa di fallimento del
  preflight che ritorna testo, il test andrà esteso per esercitare quel nuovo ramo — non
  serve un refactor del contratto finché il test copre il percorso reale.
