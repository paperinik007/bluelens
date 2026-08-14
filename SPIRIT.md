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
