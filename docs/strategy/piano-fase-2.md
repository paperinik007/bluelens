# Piano Fase 2 — dal primo audit alla maturità del metodo

Data: 2026-08-26. Da discutere. Non commit finché non condiviso con l'utente.

---

## 1. Cosa abbiamo imparato dalla Fase 1

Il primo audit (tool `aidr` di FareedKhan-dev, branch `agentpi/gap-19-20-21-agent-model-interface`) ha prodotto tre risultati, non uno solo.

### 1.1 Il risultato atteso: il detector è misurabile in modo indipendente

Il metodo funziona. 31 casi, 0 errori, pipeline riproducibile da terzi (`inspect_run`,
`regenerate_report`), confine misuratore/misurato rigido (Docker, chiavi separate, nessuna
rotta diretta `agent`↔`detector`). Ogni condizione sperimentale è dichiarata nel report
(provenance, modelli, parametri). Il metodo non è un esercizio accademico: ha prodotto un
run reale e un report pubblicabile.

### 1.2 Il risultato interessante: il detector giudica l'intento, non l'effetto

L'analisi intento-vs-effetto (`analyze_run`) mostra due cose:

- **Sulla metrica "intento"** (ground truth = `label: malicious` nel dataset, come
  presumibilmente fa il benchmark self-reported del vendor): **P=1.000** — identico a
  quanto dichiarato dal vendor (P=1.0). Zero falsi positivi su 15 benigni. Il detector
  è coerente col proprio benchmark.
- **Sulla metrica "effetto"** (ground truth = l'attacco è *davvero* riuscito nel
  transcript): **P=0.200, R=0.333**. Dei 3 attacchi realmente riusciti, il detector ne
  ha preso 1. E ha condannato 4 casi in cui l'agente aveva rifiutato.

La tabella di divergenza mostra *dove* le due metriche divergono: 9 casi in cui il
prompt era malevolo, l'agente ha rifiutato, e il detector ha detto benign → TN corretti
nell'effetto, FN nell'intento. 4 casi in cui l'agente ha rifiutato ma il detector ha
condannato comunque → FP nell'effetto, TP nell'intento.

**La scoperta non è "il detector è scarso". È che opera su un'asse diversa da quella
dell'audit**: condanna il linguaggio del prompt (ancora visibile nel turno user del
transcript), non l'effetto delle azioni dell'agente. E questa distinzione — la più
operativamente rilevante per chi compra un detector — è invisibile ai benchmark
self-reported.

### 1.3 Il risultato infrastrutturale: osservabilità e riproducibilità

Il refactor directory-per-run + `run.log` + heartbeat ha trasformato l'esecuzione da
"scatola nera che speri non si blocchi" a "processo ispezionabile in diretta". Il run
di oggi ha prodotto log completi, verificabili, collegati al commit esatto del
misuratore. `analyze_run` è uno strumento riutilizzabile. Il metodo non è solo valido:
è **comodo da usare**.

### 1.4 Limiti emersi

- **L'agente è troppo allineato.** Su 16 prompt malevoli, l'agente ne ha rifiutati 13
  (81%). Solo 3 attacchi sono realmente riusciti. La metrica "effetto" si basa su un
  campione minuscolo (TP=1, precision su 5 verdetti "malicious"). Il segnale è coerente
  (confermato su due run), ma debole numericamente.
- **Un solo vendor.** Non sappiamo se il pattern "condanna l'intento, non l'effetto" è
  specifico di `aidr` o generale. Senza un secondo vendor, il metodo non ha validazione
  esterna.
- **Dataset piccolo e poco variato.** 31 casi, 12/14 tecniche. I casi benigni collassano
  in ~8 comportamenti (correlazione nota). Lo stile dei prompt non è variato
  deliberatamente: sono per lo più diretti/espliciti. Manca la dimensione "social
  engineering educato" che il finding del 21 agosto ha isolato come vettore più
  pericoloso.

---

## 2. Cosa sappiamo misurare oggi

| Strumento | Cosa produce | Maturità |
|---|---|---|
| `run_batch` + `report.md` | Metriche primary/strict con CI, per-tecnica, setup notes complete | ✅ Pronto |
| `analyze_run` | Metriche intento/effetto + tabella divergenza | ✅ Pronto |
| `inspect_run` | Verifica riproducibile dei transcript grezzi | ✅ Pronto |
| `regenerate_report` | Ricostruzione deterministica del report da disco | ✅ Pronto |
| `run.log` + stderr | Osservabilità in tempo reale del batch | ✅ Pronto |

Tutto è verificabile da terzi senza fidarsi di noi: dataset, transcript, verdicts,
provenance sono pubblici.

---

## 3. Cosa manca per misurare meglio — tre assi prioritari

### Asse 1 — Agente più realistico (priorità massima, dipendenza per l'asse 2)

**Obiettivo**: aumentare il tasso di attacchi riusciti dal 19% (3/16) a una quota dove
la metrica "effetto" abbia potenza statistica sufficiente. Non serve un agente complesso:
servono tool che l'agente *usa* invece di rifiutare, e un modello meno allineato.

**Interventi concreti**:
- **Nuovi tool**: file system (leggere/scrivere file), API esterne simulata (webhook,
  endpoint HTTP), database con più tabelle. Tool che non attivano il "rifiuto" del
  modello perché sono operazioni legittime in sé — il malevolo sta negli argomenti,
  non nel tool.
- **Modello agente alternativo**: `gpt-4o-mini` è molto allineato. Provare un modello
  meno guard-railed (es. `claude-haiku` senza system prompt restrittivo, o un modello
  open-source via OpenRouter) per vedere se il tasso di rifiuto cala.
- **Costo**: 1-2 giorni di sviluppo + test. Non richiede nuove dipendenze.

### Asse 2 — Dataset variato deliberatamente (dipende dall'asse 1)

**Obiettivo**: espandere il dataset a ~40-50 casi, ma non per quantità — per **varietà
controllata**. Incrociare le due variabili che questo run ha isolato come rilevanti:
- **tecnica** (le 14 della tassonomia vendor, o un sottoinsieme)
- **stile di pretesto** (aggressivo/esplicito vs. educato/professionale)

Con 12 tecniche coperte × 2 stili = 24 casi malevoli, più ~12 benigni variati, si arriva
a ~40 casi. Aggiungere repliche per le tecniche con N=1 oggi (così i CI per-tecnica non
sono [0, 0.79]).

**Interventi concreti**:
- **Authoring deliberato**: per ogni tecnica, scrivere due turni seed — uno con
  linguaggio da "attacco" (come `direct_override_bulk_export_to_outsider`), uno con
  linguaggio professionale (come `bulk_export_to_partner_address`).
- **Casi benigni differenziati**: eliminare la correlazione dei 15 benigni che collassano
  in ~8 pattern (registro-limiti-aperti, voce corrispondente).
- **Costo**: principalmente authoring (lavoro umano, non codice). ~2-3 giorni.

### Asse 3 — Secondo vendor (validazione esterna del metodo)

**Obiettivo**: dimostrare che il metodo funziona senza modifiche su un detector diverso.
Se il pattern "condanna l'intento" è specifico di `aidr`, il metodo è fragile. Se si
replica su un detector diverso, il metodo è generale.

**Criteri di scelta del vendor**:
- Deve essere un detector di minacce *agentiche* (non un generico content filter / LLM
  guardrail — quello è un prodotto diverso).
- Deve avere una tassonomia di tecniche dichiarata, come `aidr` (T0001-T0014), così il
  dataset può mappare le stesse tecniche su entrambi.
- Deve essere accessibile (OSS o API pubblica) e misurabile con lo stesso harness
  (container separato + adapter).

**Interventi concreti**:
- Identificare 2-3 candidati (la ricerca di mercato `docs/research/2026-08-20-vendor-market-agentic-threat-detection.md` ne elenca diversi).
- Scrivere un adapter equivalente a `detector_adapter/` per il nuovo vendor.
- Eseguire il dataset esistente (31 casi) sul nuovo vendor → confronto diretto.
- **Costo**: 2-3 giorni per l'adapter + 1 run. Il dataset non cambia (è il punto: stesso
  dataset, detector diverso).

---

## 4. Piano concreto (sequenza)

La sequenza è forzata dalle dipendenze: l'asse 2 dipende dall'asse 1 (non puoi variare
stili di pretesto se l'agente rifiuta l'81% dei prompt). L'asse 3 è indipendente e può
partire in parallelo.

```
Asse 1 (agente) ──────> Asse 2 (dataset)
           │
           └──> Run intermedio (verifica che il tasso di attacchi riusciti sia salito)
                         │
                         └──> Run completo (nuovo agente + nuovo dataset) → report Fase 2

Asse 3 (secondo vendor) ──> Run comparativo (stesso dataset, vendor diverso) → report comparativo
```

### Milestone 1 — Agente espanso (priorità: ora)

- Nuovi tool: file I/O, endpoint HTTP simulato, query DB multi-tabella.
- Modello agente alternativo (test A/B con `gpt-4o-mini` vs. modello meno allineato).
- Verifica: il tasso di `attack_succeeded` sui 16 prompt malevoli esistenti sale almeno
  al 30-40% (oggi 19%).
- **Criterio di successo**: almeno 5-6 attacchi riusciti su 16, invece di 3.

### Milestone 2 — Dataset Fase 2 (dopo Milestone 1)

- Authoring di 24 casi malevoli (12 tecniche × 2 stili) + ~12 benigni differenziati.
- Fix dei benigni correlati (registro-limiti-aperti).
- **Criterio di successo**: il dataset carica con `load_dataset()`, tutti i criteri
  validano, nessun tool "solo malevolo" (anti-shortcut gate).

### Milestone 3 — Secondo vendor (in parallelo, indipendente)

- Adapter per un secondo detector OSS.
- Run con dataset esistente (31 casi).
- **Criterio di successo**: il metodo produce metriche confrontabili senza modifiche
  all'harness (`toy_agent` non cambia, solo `detector_adapter`).

### Milestone 4 — Report Fase 2 (integrazione)

- Run completo su nuovo agente + nuovo dataset.
- Pubblicazione con metriche intento/effetto + divergenza + confronto Fase 1.
- Se il secondo vendor è pronto, report comparativo.

---

## 5. Cosa NON fare ora

- **Non costruire 269 casi per arrivare a 300.** La quantità senza varietà controllata
  non aggiunge segnale: 300 prompt che l'agente rifiuta producono 300 FP=0 e la stessa
  P=1.0 sull'intento. Il problema non è il numero di casi — è il tasso di attacchi
  riusciti (Asse 1) e la varietà di pretesti (Asse 2).
- **Non cambiare il framework di misura prima di validarlo su un secondo vendor.** Il
  pattern "intento vs effetto" potrebbe essere specifico di `aidr`. Validare prima,
  generalizzare dopo.
- **Non aggiungere complessità all'harness.** `toy_agent` funziona. Va esteso nei tool
  (più superficie d'attacco) ma non nella struttura (pipeline, metriche, container).
- **Non correre dietro a un nome pubblico ora.** Il posizionamento dice "quando il metodo
  è stabile". Non lo è ancora: aspetta il secondo vendor.

---

## 6. Domande aperte per la discussione

1. **Modello agente alternativo**: quale? `claude-haiku` ha un bias di rifiuto simile?
   Un modello open-source via OpenRouter (`llama`, `qwen`) è meno allineato? Serve un
   esperimento rapido (1 ora di prompt engineering) prima di decidere.
2. **Secondo vendor**: quali candidati concreti dalla ricerca di mercato?
3. **Priorità relativa**: l'utente preferisce consolidare il dataset prima (Asse 2 subito,
   anche con agente attuale) o espandere l'agente (Asse 1) sapendo che sblocca un
   segnale più forte?
4. **Pubblicazione del run attuale**: il report di oggi (P=0.200 effetto, P=1.000
   intento) è pubblicabile come "Fase 1 completata" o va tenuto come interno finché non
   c'è un secondo run di conferma?