Sei un lettore esterno del pacchetto di congelamento di un esperimento: il progetto BlueLens misura quanto bene alcuni rilevatori di attacchi
contro agenti AI (PromptGuard, AlignmentCheck, aidr) riconoscono attacchi costruiti a mano. Il testo e il codice che leggi li ha scritti un altro
modello (Claude) insieme al proprietario del progetto: tu sei di un'altra famiglia e il tuo compito è trovare ciò che chi li ha scritti non vede.
Non hai accesso al repository, non hai strumenti, non puoi fare domande: hai solo il testo incollato qui sotto, e rispondi in un solo giro.
Rispondi in italiano.

# La domanda, una sola
Se il proprietario approva oggi questo pacchetto e lo pubblica, c'è qualcosa che lo rende non verificabile da un lettore esterno, interno
contraddittorio, o che lascia scegliere le regole di conteggio guardando i risultati? Dopo la pubblicazione il run non si cambia: un
cambiamento è un run nuovo e quello vecchio resta com'è.

# Cosa guardare, in ordine
1. **Le differenze** (sezione «DIFFERENZE»): sono le modifiche fatte dopo che un gruppo di revisori (il council del 12 novembre) aveva letto il
   testo. Le correzioni sono coerenti con il resto del piano? Hanno lasciato contraddizioni: numeri che non tornano, comandi diversi da quelli
   descritti altrove, nomi di file o di punti che non esistono più, una regola che dice una cosa in un posto e il contrario in un altro?
2. **L'elenco A** (sezione «ELENCO A»): il piano dice cosa si congela (parte 12, «Cosa si congela»). L'elenco lo contiene tutto? C'è qualcosa
   che i programmi nuovi leggono per calcolare i risultati e che non è nell'elenco, così che si potrebbe cambiare dopo senza che nessuno lo veda?
3. **I programmi nuovi** (`analisi_v3.py`, `elenco_a.py`, `registra_versioni.py`): fanno ciò che il piano dice? Dove il codice decide una regola
   di conteggio che il piano non fissa, dillo. Dove un caso limite può dare un numero sbagliato senza fermarsi, dillo.
4. **I principi del progetto** (`SPIRIT.md`): in particolare «la metodologia prima dei risultati» e «l'onestà statistica». Una scelta li viola?

# Cosa NON fare
- **Non ripetere i limiti già dichiarati.** La pagina dei limiti (voci numerate) elenca ciò che gli autori già sanno essere imperfetto. Se un
  tuo punto è già in una voce, scrivilo nella sezione finale «Già dichiarato», una riga, con il numero della voce, e non altro.
- **Non riproporre i punti già valutati** da specialisti e council (documenti nella sezione «GIÀ VALUTATO»): se coincidono, una riga in «Già valutato».
- Non proporre nuove analisi, nuove viste o nuovi casi. Non giudicare la scelta dei modelli. Non commentare lo stile.
- Non inventare cifre: ogni numero che citi deve stare nel testo che ti è stato dato, con il punto in cui sta.

# Formato dell'uscita
Al massimo **12 punti**, ordinati per gravità. Per ciascuno:
- **Titolo** breve.
- **Gravità:** `BLOCCA` (cambia cosa si congela, rende il run non verificabile, o permette di scegliere una regola dopo aver visto i risultati),
  `CAMBIA` (cambia come si formulano le affermazioni pubbliche o i limiti), `MINORE`.
- **Cosa non torna:** una o due frasi.
- **PROVA:** una citazione letterale (al massimo due righe) con il documento e la sezione o, per il codice, il nome della funzione. Se non puoi
  verificarlo dal solo testo, scrivi `SOLO TESTO` e dì che cosa servirebbe vedere.
- **Correzione proposta:** una riga.

Poi tre sezioni brevi: «Già dichiarato» (voce della pagina dei limiti), «Già valutato» (documento), «Non ho potuto verificare» (cosa
richiederebbe il repository).

# Onestà
Se non trovi nulla di grave, scrivi «nessun punto che blocchi» e fermati: non riempire fino a 12. Un elenco corto e vero vale più di uno lungo.
Distingui sempre ciò che hai letto da ciò che supponi.
