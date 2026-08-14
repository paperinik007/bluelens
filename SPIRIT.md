# Spirito del progetto

## Perché esiste questo repo

Sta nascendo un mercato di prodotti che promettono di rilevare comportamenti malevoli
negli agenti AI ("agentic threat detection", "guardrails", ecc.). I benchmark che
accompagnano questi prodotti sono quasi sempre **self-reported**: lo stesso team che
costruisce il detector costruisce anche il benchmark che lo valuta. Non esiste ancora,
in modo sistematico, un equivalente di un ente di certificazione indipendente per
questo settore.

Questo repo è il punto di partenza per diventare quella figura indipendente: non un
altro vendor, ma chi testa i vendor con metodologia trasparente, dataset propri e
risultati pubblicati per intero — inclusi i limiti statistici delle proprie stesse
misure.

## Cosa NON è questo progetto

- Non è un tentativo di costruire l'ennesimo tool di detection da vendere.
- Non è un esercizio accademico fine a sé stesso: ogni audit deve produrre un output
  pubblicabile e verificabile da terzi.
- Non è un'attività "gotcha" contro i vendor testati: l'obiettivo è rigore, non
  smontare per principio. Un audit onesto può anche confermare che un tool funziona
  bene quanto dichiara.

## Principi metodologici

1. **Dataset indipendente.** Ogni audit usa casi di test costruiti da zero, mai il
   benchmark fornito dal vendor — altrimenti si misura solo quanto il vendor si è
   tarato sul proprio compito.
2. **Metodologia dichiarata prima dei risultati.** Ogni caso di test viene definito
   (tecnica target, esito atteso, ragionamento) *prima* di eseguire il tool, per
   evitare bias di conferma nell'interpretazione dell'output.
3. **Onestà statistica.** Con campioni piccoli, dichiarare esplicitamente intervalli
   di confidenza o limiti di generalizzabilità — mai presentare un numero secco come
   se fosse una verità assoluta (è esattamente il difetto che questo progetto
   contesta ai benchmark dei vendor).
4. **Riproducibilità.** Dataset, codice del toy agent e risultati grezzi pubblicati
   insieme all'analisi, non solo le conclusioni.
5. **Indipendenza economica.** Se in futuro questo lavoro genera compensi, la
   struttura deve restare quella di chi è pagato da chi valuta un acquisto, mai da chi
   vende il prodotto sotto test — è l'unico asset reale di questo ruolo.
6. **Pubblicazione e disclosure responsabile.** Tutto ciò che serve a verificare in modo
   indipendente un risultato viene pubblicato: metodologia, dataset, risultati grezzi —
   non solo le conclusioni (vedi principio 4). Questo include, esplicitamente, il codice
   del **misuratore** (schema dati, adapter, modulo metriche, generatore del report):
   è lo strumento che giudica il tool sotto test, quindi è il pezzo con l'obbligo di
   trasparenza più stringente di tutti — un misuratore che dichiara di essere imparziale
   ma non è verificabile da terzi ricade esattamente nel difetto "self-reported" che
   questo progetto contesta ai vendor (vedi "Perché esiste questo repo"). Gli unici
   elementi esclusi dalla pubblicazione sono credenziali/segreti, l'eventuale immagine
   container costruita (si pubblica il suo sorgente, non il binario), e codice di terze
   parti già pubblico altrove, che si referenzia (commit pinnato) invece di
   ripubblicare. Se un audit fa emergere una debolezza specifica del tool testato che
   potrebbe leggersi come un attacco mirato al maintainer, si dà un preavviso prima o
   contestualmente alla pubblicazione — coerente col principio che questo non è
   un'attività "gotcha".
7. **Il moat è la reputazione, non la segretezza.** Pubblicare tutto (principio 6)
   significa che chiunque può copiare il misuratore e mettersi in concorrenza — non è un
   rischio da mitigare con la segretezza (vanificherebbe l'intero progetto), perché non
   è mai stato lo strumento a rendere affidabile un ente di certificazione indipendente:
   MITRE ATT&CK e la metodologia OWASP sono completamente pubbliche, eppure chi le
   applica resta distinguibile per storico di rigore accumulato, non per un metodo
   segreto. Coerentemente col modello economico del principio 5 (pagati da chi valuta un
   acquisto, non da chi vende), il valore che si vende non è mai l'accesso esclusivo al
   tool, è il giudizio applicato con una firma che se ne assume la responsabilità. Il
   rischio reale non è "qualcuno copia bene" ma "qualcuno forka male e confonde il
   mercato" — la difesa è l'attribuzione forte (ogni report riporta il commit esatto del
   misuratore che l'ha prodotto, principio 4) e una licenza che obblighi chi forka il
   codice a restare altrettanto trasparente (tipo copyleft/share-alike), così che chi
   copia questo lavoro e poi lo richiude diventi visibilmente il vendor opaco che questo
   progetto contesta.

## Primo obiettivo concreto (Fase 1)

Audit indipendente di un primo tool reale (`agentic-threat-detection` di
FareedKhan-dev) usando:
- un toy agent costruito qui, con tool realistici ma controllati
- un dataset di attacchi/casi benigni costruito a mano sulle 14 tecniche della
  tassonomia dichiarata dal tool, poi arricchito con casi ispirati a incidenti reali
  documentati
- misurazione di precision/recall/F1 con dichiarazione esplicita dei limiti del
  campione, confrontata con i numeri dichiarati dal vendor (P=1.0, R=0.667 su 300
  sessioni, 42 malevole)

Il design tecnico del toy agent e del dataset di attacchi verrà trattato come design
doc separato, con relativo giro di review, prima di iniziare l'implementazione.
