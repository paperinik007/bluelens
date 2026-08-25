# Verifica run esistenti — Gap 19/21

Data: 2026-08-25. Eseguito dopo l'implementazione di `inspect_run.py` (Task 15) sul
branch `agentpi/gap-19-20-21-agent-model-interface`.

**Comando riproducibile** (da qualunque checkout che include `inspect_run.py`):

```
python -m toy_agent.inspect_run <run_directory>
```

---

## 1. Run pubblicato: `docs/reports/agentic-threat-detection-2026-08-19/`

```
transcript_count: 31
tool_calls: 46
empty_arguments: 0
non_dict_arguments: 0
arguments_parse_failed: 0
model_retries: 0
stop_reasons: {completed: 31}
missing_transcripts: []
stale_transcripts: []
provenance: not recorded
```

**Conclusione**: esente da Gap 19 e Gap 21. I 31 transcript sono tutti tracciati da git
in questa directory — chiunque abbia il repo può eseguire il check e ottenere lo stesso
risultato (principio 4, SPIRIT.md).

**Provenance**: non registrata al tempo del run. Gap 20 era aperto: nessuna condizione
sperimentale è stata catturata. Il modello agente era `openai/gpt-4o-mini` (hardcoded
nel codice al commit `0745490`, ultimo commit toccante `src/` prima del run). I modelli
detector (SIFTER_MODEL, INSPECTOR_MODEL, EMBED_MODEL) erano variabili d'ambiente
dell'host, non registrate — è esattamente ciò che Gap 20 esiste per impedire.

---

## 2. Run parcheggiato: `run_output/`

```
transcript_count: 31
tool_calls: 44
empty_arguments: 0
non_dict_arguments: 0
arguments_parse_failed: 0
model_retries: 0
stop_reasons: {completed: 31}
missing_transcripts: []
stale_transcripts: []
provenance: not recorded
```

**Conclusione**: esente da Gap 19 e Gap 21. 0 argomenti vuoti su 44 chiamate — per
necessità (non sufficienza) questo esclude la contaminazione. 0 argomenti non-dict —
la verifica aggiuntiva introdotta da council-risk (punto 12) conferma l'assenza del
punto cieco. 0 retry.

### Provenance ricostruita

Ricostruita dopo il fatto dai timestamp dei file e dalla git history. Il run è stato
prodotto il **2026-08-21 alle 11:10**, quando HEAD su master era `4a644a2` (docs-only,
10:42). L'ultimo commit toccante `src/` era `0745490` (10:09), il cui contenuto di
codice è identico a `4a644a2`. Il vendor pin nel Dockerfile era
`7fad14d2478707e68a09b8ecd9942dec8fde1614`, invariato dal commit `b2c3e77`
(2026-08-16).

| Condizione | Valore | Certezza |
|---|---|---|
| measurer_commit | `4a644a2` | Ricostruito dai timestamp — il contenuto del codice è `0745490` |
| measurer_dirty | non determinabile | Nessun record al tempo del run |
| vendor_commit | `7fad14d2478707e68a09b8ecd9942dec8fde1614` | Certo — invariato dal 2026-08-16 |
| agent_model | `openai/gpt-4o-mini` | Certo — hardcoded nel codice |
| sifter_model | non registrato | Variabile d'ambiente host, mai catturata |
| inspector_model | non registrato | Idem |
| embed_model | non registrato | Idem |
| cost_source | local pricing table | Certo — pre-fix |

**Incertezza dichiarata**: non sappiamo se il working tree fosse dirty, né quali
modelli detector fossero configurati. Sono esattamente le due informazioni che
`provenance.py` ora cattura automaticamente e che questo documento non può
ricostruire — Gap 20 in azione.

---

## 3. Costi detector (evidenza dal thin-proxy log)

Recuperati dal log già pubblicato. 519 risposte vendor su 519 portano un campo
`cost`. Il costo totale del detector per l'intero run è **$0.013647** (media
$0.00044/caso, massimo $0.00167). Comando per ricomputare:

```
grep -o '"cost":[0-9.]*' docs/reports/.../thin_proxy.log | cut -d: -f2 | paste -sd+ | bc
```

---

## 4. Limiti dichiarati

1. **Contingente, non strutturale** (principio 8, SPIRIT.md): questo accertamento
   dice che *questi* due run sono sani, non che il codice sia corretto. Il fix
   (Task 1-15) resta necessario per costruzione.
2. **Campione minuscolo**: 44 e 46 chiamate rispettivamente. "Zero fallimenti su
   44/46" non autorizza a concludere che il fenomeno sia raro in generale.

---

## 5. Decisione sul run parcheggiato

Confermata la decisione presa con l'utente il 2026-08-21: **il run parcheggiato NON
viene pubblicato**. Dopo questo piano, un run fresco non ha nessuno dei suoi
inconvenienti (provenance catturata alla fonte, modelli detector registrati, costi
dalla risposta). Pubblicare ora un secondo numero pre-fix metterebbe in circolazione
una misura che dovremmo comunque rifare. Il run è tenuto per mostrare che il fix non
inseguiva un problema immaginario — scopo servito da questo stesso documento.

`run_output/` è in `.gitignore` e il primo run post-fix lo sovrascriverà,
`provenance.json` incluso. **Il record git-tracked è questo documento.**