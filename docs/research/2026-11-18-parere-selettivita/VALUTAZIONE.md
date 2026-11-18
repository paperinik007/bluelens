# Valutazione del parere esterno sulla selettività (18 novembre 2026)

Modello `qwen/qwen4-max` (Alibaba), un giro, 0,030 dollari (5306 token in ingresso, 5353 in uscita). Verdetto del modello: **CONCORDO CON RISERVE** sulla
strada 2. Ogni punto è stato verificato su documenti e codice prima di accoglierlo.

| Punto del parere | Esito | Verifica |
|---|---|---|
| Fatto 2: esiste una terza lettura, «solo azioni» di aidr: fuori sfera 9, non 2 | **Accolto** (omissione mia) | calcolato dalle schede e da `AIDR_ACTIONS`: dentro 28, fuori 9 (la tabella del piano dice 28) |
| Fatto 2: «eseguire comandi» ha solo 2 casi (n13, c05) contro la regola «almeno 3» | **Da guardare, estraneo alla decisione** | la riga della tabella del piano (655) dice «n13 e c05 per l'azione»; non ho verificato se altri casi della forma coprano la casella |
| Fatto 3: «i verdetti esistono» non è verificabile | **Accolto: la frase era imprecisa** | il run non è ancora stato fatto, nessun verdetto esiste; è vero solo che il codice non filtra per ambito, quindi i giudici girano su tutte le sessioni |
| Fatto 4: «`if fuori or _in_ambito` rietichetta come benigna, forse un bug che tocca i numeri» | **Scartato: dubbio nato da un estratto incompleto mio** | `fuori = benigno and gruppo == "danno" and lettura != "wide"` (solo il danno dei benigni, voce 16); il pacchetto non riportava quella riga |
| Fatto 5: «restano accanto» prescrive la collocazione, non autorizza l'omissione | **Accolto** | è sotto «Affermazioni ammesse, scritte prima» (parte 13, punto 3) |
| Fatto 6: la vista per minaccia include già il fuori sfera | **Accolto in parte** | dice cosa il giudice dichiara di coprire (da `ambito.json`), non cosa ha fatto fuori sfera |
| Fatto 7: la strada 2 vale come voce 7 solo se la definizione ha prova di data e nessuno ha guardato i verdetti fuori sfera | **Accolto, le due condizioni valgono** | il piano è nel gruppo «documenti» dell'elenco A (si pubblica al push); nessun verdetto esiste ancora |
| Quarta strada: dichiarare ora il denominatore (quanti casi dentro e quanti fuori sfera) | **Accolto** | si ricava solo da `ambito.json`, già caricato; non dipende dai verdetti |
| aidr ha 2 casi fuori sfera: numero secco vietato (SPIRIT 3) | **Accolto per la definizione** | si riusa la regola esistente «meno di 3 casi: nessuna frase» |
| Molteplicità: letture, soglia di maggioranza e pari vanno fissati ora per tutte le letture | **Accolto** | si scrive nella definizione |
| SPIRIT 6: il codice scritto dopo il congelamento non sta nell'elenco A | **Accolto** | citazione verificata («esenta per omissione proprio ciò che è stato aggiunto per ultimo»); rimedio: il codice sta nel repository pubblico e il rapporto nomina il suo commit |

Conclusione: la raccomandazione di Claude (strada 2) regge, con un'aggiunta: **strada 2+**. Definizione completa scritta ora nel piano; subito, nel codice e nel
rapporto, solo il denominatore (casi malevoli in tutto, dentro la sfera, fuori sfera) per giudice e per lettura; il blocco con i verdetti fuori sfera si scrive dopo
il congelamento, con l'etichetta e il commit pubblico nominato nel rapporto.
