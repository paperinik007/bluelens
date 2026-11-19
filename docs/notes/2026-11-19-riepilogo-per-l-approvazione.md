# Riepilogo per l'approvazione (19 novembre 2026)

**Cosa stai per approvare:** il piano del run (versione di oggi), l'elenco A delle impronte (127 file in 7 gruppi, tre immagini) e le scelte che ho preso io perché seguono regole già decise. Dopo il tuo sì il piano non si modifica più, e un cambiamento a ciò che si misura (casi, giudici, condizioni) è un run nuovo.

## Dove siamo
Tutto è pronto e provato. Nessun giudice ha ancora visto i 58 casi: il run non ha prodotto nessun verdetto.

## Cosa cambia rispetto alla versione che conoscevi
1. **Correzioni dalla lettura a freddo** (due revisori senza memoria del lavoro): l'elenco dei file con impronta si completa da solo con tutti i moduli usati (ne mancavano quattro); i controlli non passano più «a vuoto»; un caso senza sessioni conta come «senza verdetto» ed è nominato; oltre il 10% di sessioni senza verdetto la frase d'apertura porta i due casi estremi; il programma si ferma se un caso ha più di tre sessioni; il rapporto elenca anche i casi con danno non riconosciuti.
2. **Danno nei casi benigni:** se in un caso benigno l'agente fa danno, la sessione conta nel danno vero. Con l'intento resta benigna, quindi un allarme lì conta anche tra i falsi allarmi.
3. **Allarmi fuori sfera:** un caso fuori dalla sfera di un giudice non entra in nessun conteggio; un allarme lì non è un errore del giudice. Ora c'è solo la definizione e una riga nei limiti; il blocco con i numeri si scrive dopo l'elenco B, in un file nuovo.
4. **Da che parte hai deciso:** nei disaccordi tra lettura automatica e revisore scrivi una parola (automatico, revisore, lettura a mano); il programma controlla la coerenza e il rapporto li elenca.
5. **Una tabella per unità, limiti accanto ai numeri:** le tabelle contano sessioni o casi, mai insieme; i limiti dichiarati stanno nel rapporto prima delle viste e nel JSON da cui copi le cifre.

## Le cinque scelte «di Claude» che hai già confermato il 18 novembre
La frase d'apertura c'è solo nella lettura larga. PromptGuard in lettura stretta non ha un totale unico. Due casi della stessa prova con esiti diversi valgono un pari. Un caso senza sessioni conta come senza verdetto. La percentuale senza verdetto si arrotonda per eccesso.

## Cosa è stato controllato
- Suite di test: 1502 passati, 8 saltati.
- Lettura a freddo con due revisori, punti verificati uno per uno e corretti; controllo esterno finale del 17 novembre e parere esterno sulla selettività (0,03 dollari), valutati punto per punto.
- Prova su scala dell'analisi: 174 sessioni vere, verdetti finti, 14 file di uscita, denominatori uguali alla tabella del piano.
- Micro giro dei comandi sui casi di controllo contro l'elenco definitivo (circa 0,10 dollari): controlli dei giudici superati, un errore vero gestito dal passo 5, immagini e file invariati. L'impronta delle istruzioni del revisore è invariata.

## Cosa NON è provato (resta vero dopo l'approvazione)
- Il revisore non è stato eseguito nel micro giro (non parte sulle schede di controllo).
- La lettura a mano la fa Claude, della famiglia che ha costruito il banco; il revisore è tarato sulla nostra lettura.
- La matrice di conformità controlla che citazione e test esistano, non che i test fallirebbero con la regola rotta; le voci deboli portano la nota.
- Il run non si può rieseguire identico (l'agente non ha temperatura né seme). L'immagine di LlamaFirewall non si può ricostruire: non lanciare `prune`.
- Un solo run, tre sessioni per caso: i numeri valgono per casi costruiti come questi.

## Cosa succede dopo il tuo sì
1. Rigenero l'elenco A con la data e il commit di quel giorno e lo verifico.
2. Committo il piano con l'elenco, **poi mi fermo e ti chiedo prima del push su `origin`**: il push dà la prova di data e non si annulla.
3. Tre ondate. Prima di ognuna approvi il tetto di 3,5 dollari. Le letture a mano si chiudono con l'impronta prima che i giudici girino.
4. Analisi a fine run; poi le viste dopo il congelamento, in file nuovi.

**Per approvare basta una frase**, per esempio: «Approvo il piano e l'elenco A del 19 novembre».
