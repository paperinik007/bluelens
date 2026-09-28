# Protocollo di revisione indipendente della chiave di lettura

Revisione in due fasi della regola meccanica (`../interpretation_key.py`, chiave di lettura
sezione 5), pensata perché il revisore non si limiti a convalidarla.

1. **Fase 1, alla cieca** (`FASE-1-ISTRUZIONI.md`). Il revisore riceve un pacchetto con
   solo il codice dell'agente e degli strumenti, il dataset e i 138 transcript, con i
   run rinominati `run_A`…`run_E` (ordine casuale, seed `20260928`). Non riceve i
   verdetti dei detector, i report, i Gap 22-24, la chiave di lettura, né la regola.
   Classifica ogni coppia run-caso in base al solo principio.
2. **Fase 2** (`FASE-2-ISTRUZIONI.md`), consegnata solo dopo la Fase 1: il revisore
   critica la regola usando la propria classificazione come termine di paragone.
3. **Confronto**: `python compare_review.py <classificazione.csv> <mapping.json>`
   confronta la classificazione del revisore con la regola, coppia per coppia. La
   mappa dei run rinominati viene scritta fuori dal pacchetto quando lo si costruisce.
