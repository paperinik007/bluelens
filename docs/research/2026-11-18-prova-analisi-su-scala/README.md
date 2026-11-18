# Prova generale dell'analisi su scala reale (18 novembre 2026)

Cosa è: `analisi_v3.py` fatto girare per intero, con la riga di comando del run, su dati della dimensione vera: le 174 sessioni vere della prova generale
dell'agente (58 casi × 3) e le 58 schede e `ambito.json` veri. I verdetti sono FINTI (pseudo-casuali, con qualche verdetto mancante e qualche terzo verdetto):
la prova non misura niente, controlla che il programma regga e che i denominatori tornino con il piano. Le 24 sessioni dei casi «solo testo» hanno una lettura
chiusa finta («nessun danno»).

Come si rifà (cartelle fuori dal repository):
    python docs/research/2026-11-18-prova-analisi-su-scala/prova_analisi.py CARTELLA_ONDATA
    PYTHONPATH=src python -I -m toy_agent.analisi_v3 CARTELLA_ONDATA --schede dataset_v3/cases --ambito dataset_v3/ambito.json \
        --plausibilita docs/research/2026-11-05-revisore/schede-plausibilita --out CARTELLA_USCITA

## Esito (commit 30fffd2 più le correzioni di quel giorno)
- 14 file di uscita, nessun errore.
- Casi per giudice, lettura larga: PromptGuard 26 (tabella del piano: 26); AlignmentCheck 16 con attacco + 3 «agente» = 19 (19); aidr 32 + 3 = 35 (35);
  aidr solo azioni 25 + 3 = 28 (28). Benigni 21 in tutti. Nessun caso senza sessioni. Nessun benigno con danno (come nella prova generale).
- Da rifare dopo ogni modifica a `analisi_v3.py` prima del congelamento.
