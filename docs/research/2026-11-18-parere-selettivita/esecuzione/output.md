# Controllo finale esterno (qwen/qwen4-max, fornitore Alibaba)

**CONCORDO CON RISERVE**

## 1. Fatti

- **1** sostenuto (PIANO 372‑376), ma lì resta aperto «cos'è una casella»: il 9 ottobre la sfera non era congelata.
- **2** larga verificabile (tabella 651‑660: 11/18/2). Stretta: NON VERIFICABILE (`ambito.json` non incollato), solo coerente per aritmetica (37−8/16/3). Due omissioni: (a) il codice ha una **terza** lettura, `actions_only` (CODICE, `_in_ambito`), che la tabella dà 28 in ambito per aidr → ~9 fuori, non 2; (b) la tabella assegna a "eseguire comandi" **2** casi (n13, c05) contro la regola «almeno 3» (372‑376 e 659‑660): incoerenza interna che sposta i confini di sfera, quindi i conteggi.
- **3** NON VERIFICABILE (`judge_sessions.py`, `prepare_judge_input.py` non incollati).
- **4** solo parziale, e con un dubbio serio. La riga `if fuori or _in_ambito(...)` con `"benigna" if fuori else gruppo` (CODICE, "dove si scartano") **ri‑etichetta «benigna»** le sessioni marcate `fuori`, la cui definizione non è incollata. Se `fuori` coprisse anche malevoli fuori sfera, il fatto 4 è falso e c'è un bug che tocca i numeri in testa (12 nov, 6a). Da chiarire **prima** del congelamento. «Nel rapporto non compare da nessuna parte»: NON VERIFICABILE (due frammenti).
- **5** citazione esatta, lettura riduttiva: sta sotto «Affermazioni ammesse, **scritte prima**»; «restano accanto» prescrive la collocazione, non autorizza l'omissione.
- **6** sostenuto (voce 7), e la vista per minaccia **già include** il fuori sfera («non dichiara di coprirlo», da `ambito.json`): parte della selettività è dunque già prevista dopo il congelamento.
- **7** regola Pareto NON VERIFICABILE (non incollata). Il 12 nov punto 6 è incollato e distingue **6b** (vista non prevista → «aggiunta dopo aver visto i risultati») dalla voce 7 (pre‑definita). La strada 2 appartiene alla seconda categoria **solo a due condizioni**.

## 2. Ragioni

La garanzia della strada 2 non è «il piano lo dice»: è (i) prova di data della definizione e (ii) **nessuno ha guardato i verdetti fuori sfera**. Il fatto 3 dice che i verdetti *esistono*: esistenza ≠ lettura, ma il testo non dimostra la seconda. Serve una dichiarazione scritta del proprietario («nessuna lettura dei verdetti fuori sfera alla data X») e che il piano sia committato al push di congelamento — se il piano è dentro elenco A: NON VERIFICABILE. Se salta una delle due, l'etichetta corretta è 6b, non voce 7.

**Quarta strada (2+)**, costo poche righe: subito, nel rapporto principale e nei limiti, il **fatto di disegno** — per giudice e per lettura, quanti malevoli entrano nel denominatore e quanti restano fuori (11/18/2 larga). Non è un risultato, è il denominatore, e viene da `ambito.json` già caricato. Senza, un lettore legge «recall su 19 casi» come se fosse su 37. «Mai in testa» vieta la selettività *come metrica di testa*, non la dichiarazione che la sfera è un sottoinsieme. Il blocco coi verdetti resta dopo, con etichetta e commit pubblicato.

## 3. Cosa manca

- **aidr n=2**: numero secco vietato (SPIRIT 3); il piano stesso lo dichiara piccolo (659‑660). Con 11/18 casi e maggioranza di sessioni, servono intervalli o la dicitura «non stimabile».
- **Molteplicità**: larga/stretta/`actions_only`, soglia di maggioranza e caso di pari vanno fissati ora per *tutte* le letture, con obbligo di riportarle tutte; altrimenti è scelta di conteggio a posteriori (11 nov punto 2, richiamato nel 12 nov punto 6).
- **Elenco A come perimetro**: SPIRIT 6 definisce il misuratore «per criterio e non per elenco» e avverte che l'elenco «esenta per omissione proprio ciò che è stato aggiunto per ultimo». È esattamente la forma della strada 2. Fuori da elenco A ≠ fuori dalla pubblicazione: il codice va pubblicato e pinnato nel report (SPIRIT 6/7).
- **Interesse dell'autore**: dichiarato, ma coincide con l'opzione più fragile sulla prova di data; il differenziale di costo è piccolo, quindi non giustifica la fragilità.
