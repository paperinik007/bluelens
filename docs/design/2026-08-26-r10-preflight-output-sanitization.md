# R10 — Output del preflight non sanitizzato a valle del tipo di ritorno

Data: 2026-08-26. Stato: **analisi e soluzione proposta, non implementata** (declassata a
bassa priorità, da riprendere quando si riaprirà il lavoro sul preflight). Riferita da
`docs/design/registro-limiti-aperti.md`, voce "`run_batch.main()` si fida ciecamente
dell'output di `preflight_check_models`".

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

## 4. La soluzione strutturale: tipizzare il ritorno del preflight

Il gap si chiude solo cambiando **il contratto** del preflight: non restituire più testo
libero, ma dati strutturati, e lasciare a un unico formattatore il compito di produrre il
messaggio usando solo campi tipizzati.

```python
@dataclass(frozen=True)
class PreflightFailure:
    tier: str        # "sifter" | "inspector" | "embed" | "agent"
    model: str       # il model id
    kind: str        # "http" | "exception" | "missing_key"
    detail: str      # già sanificato: status code | class name | literal

    def as_message(self) -> str:
        # unico punto che costruisce il testo destinato al log
        ...
```

- `preflight_check_models` ritorna `list[PreflightFailure]`.
- `_probe()` continua a sanificare a monte: `detail` riceve solo `str(exc.response.status_code)`
  o `exc.__class__.__name__` — mai `str(exc)`.
- `main()` stampa solo `failure.as_message()`, mai una stringa opaca. Il testo raw non ha
  alcun campo in cui entrare: il tipo è il filtro.

### 4.1 Invariante di verifica (il test che chiude davvero R10)

End-to-end, senza fake che aggira: preflight **reale** + `httpx.MockTransport` che solleva
`Boom("Authorization: Bearer sk-SENTINEL-not-a-real-key")` → eseguire `main()` (con
`execute_batch` mockato) e asserire che `run.log` **non contenga** `SENTINEL`. Con il tipo
strutturato, il raw text non ha alcun percorso verso l'output.

## 5. Impatto e tier

| File | Modifica |
|---|---|
| `src/toy_agent/preflight.py` | `PreflightFailure` dataclass + `_probe`/`preflight_check_models` ritornano il tipo |
| `src/toy_agent/run_batch.py` | `main()` stampa `failure.as_message()` |
| `tests/toy_agent/test_preflight.py` | ~10 test: i confronti su stringa diventano su campi del dataclass |
| `tests/toy_agent/test_run_batch.py` | 2 fake (`["model unavailable"]`) + riscrittura del test R10 end-to-end |

Criteri di tiering (`docs/notes/pi-point-1-tiering.md`): "tocca 3+ file in moduli diversi"
→ **Light** (design sketch + council skeptic/pragmatist + griller). Non tocca `schema.py`,
non cambia il confine `toy_agent`/`detector_adapter`, non introduce dipendenze.

## 6. Stato e riattivazione

- **Oggi**: registrata come limite aperto (rischio latente), con questa analisi come
  punto di partenza per l'implementazione.
- **Quando riaprirla**: insieme al prossimo lavoro che tocca `preflight.py` o `run_batch.py`
  (es. una nuova causa di fallimento del preflight, o la pubblicazione automatica
  `python -m toy_agent.publish` che porta con sé il run.log), o quando si decide che il
  vincolo "nessun raw text" va garantito per costruzione su tutta la catena di log.
- **Costo stimato**: basso (un dataclass + adattamento dei test esistenti); il rischio di
  regressione è basso perché `as_message()` riproduce il formato attuale
  `"{tier} ({model}): HTTP {code}"` / `"{tier} ({model}): {Class}"`, così i consumatori
  esistenti non cambiano output.
