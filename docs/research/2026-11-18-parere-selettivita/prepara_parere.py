import hashlib, json, pathlib, subprocess

REPO = pathlib.Path(r"C:\Users\salva\Documents\github\agentic-security-audits")
OUT = REPO / "docs/research/2026-11-18-parere-selettivita/esecuzione"
OUT.mkdir(parents=True, exist_ok=True)

def blob(path):
    r = subprocess.run(["git", "cat-file", "blob", f"HEAD:{path}"], cwd=REPO, capture_output=True, stdin=subprocess.DEVNULL, check=True)
    return r.stdout.decode("utf-8").replace("\r\n", "\n")

def righe(path, a, b):
    return "\n".join(blob(path).split("\n")[a - 1:b])

PIANO = "docs/design/2026-10-11-piano-run-v3.md"
SFERE = "docs/design/2026-10-11-sfere-giudici.md"
estratti = [
    ("PIANO, parte sulla copertura (righe 372-376)", righe(PIANO, 372, 376)),
    ("PIANO, parte sul dataset: «selettività senza casi in più» (righe 396-404)", righe(PIANO, 396, 404)),
    ("PIANO, tabella dell'ambito atteso per giudice (righe 651-660)", righe(PIANO, 651, 660)),
    ("PIANO, parte 13 punto 3: affermazioni ammesse (righe 1563-1567)", righe(PIANO, 1563, 1567)),
    ("PIANO, Aggiunte del 12 novembre, punto 6: modifiche dopo aver visto i risultati", righe(PIANO, 1744, 1755)),
    ("PIANO, Aggiunte del 17 novembre, voce 7: cosa si scrive dopo il congelamento", righe(PIANO, 1779, 1782)),
    ("PAGINA DELLE SFERE, riga 47 (PromptGuard, forma esplicita)", righe(SFERE, 47, 47)),
]
codice = [
    ("CODICE analisi_v3.py: appartenenza di un caso alla sfera di un giudice", "\n".join(
        blob("src/toy_agent/analisi_v3.py").split("\n")[blob("src/toy_agent/analisi_v3.py").split("\n").index("def _in_ambito(scheda: dict, caso: str, giudice: str, lettura: str, ambito: dict) -> bool:"):][:10])),
    ("CODICE analisi_v3.py: dove si scartano le sessioni fuori sfera", "\n".join(
        l for l in blob("src/toy_agent/analisi_v3.py").split("\n") if "for g in giudici:" in l or "fuori or _in_ambito" in l or "risultato[g].append(Sessione" in l)),
]
spirit = blob("SPIRIT.md")

analisi = """# Il problema da decidere

Il progetto BlueLens misura quanto bene tre rilevatori di attacchi contro agenti AI (PromptGuard, AlignmentCheck, aidr) riconoscono 37 attacchi
costruiti a mano (casi malevoli), più 21 casi benigni. Ogni rilevatore (giudice) dichiara di coprire certi attacchi: la sua SFERA. I casi malevoli
che stanno fuori dalla sfera di un giudice sono «fuori sfera».

## I fatti (verificati da Claude sul codice e sui documenti; tu verifica quelli che il testo incollato ti permette di verificare)
1. Il dataset ha casi fuori sfera DI PROPOSITO, decisi dal proprietario il 9 ottobre «per la selettività» (vedi PIANO, righe 372-376 e 396-404).
2. Quanti sono. Lettura larga: fuori sfera 11 casi su 37 per PromptGuard, 18 per AlignmentCheck, 2 per aidr. Lettura stretta: 29, 21, 34. (Calcolati
   da `dataset_v3/ambito.json`; la tabella del piano, righe 651-660, dà gli stessi ordini di grandezza per la lettura larga.)
3. I tre giudici girano su TUTTE le sessioni, anche su quelle fuori sfera: i moduli `judge_sessions.py` e `prepare_judge_input.py` non contengono
   nessun filtro per ambito (cercato `ambito`, `scope`, `in_scope`: nessuna occorrenza). Quindi i verdetti sui casi fuori sfera ESISTONO.
4. Il programma di analisi (`analisi_v3.py`) quando carica le sessioni scarta quelle fuori sfera (vedi CODICE sotto): nel rapporto non compare da
   nessuna parte cosa hanno fatto i giudici fuori sfera. Un allarme lì non cambia nessun numero.
5. Il piano (parte 13, punto 3, righe 1563-1567) dice: «I gemelli e la selettività restano accanto, mai in testa». Cioè: se si riportano, non vanno
   nella frase d'apertura né nei risultati principali. Non dice come si calcolano né se sono obbligatori nel rapporto.
6. Il piano ha già una categoria di viste «scritte dopo il congelamento»: la vista per minaccia e il conteggio delle sessioni guaste con passo
   malevolo (Aggiunte del 17 novembre, voce 7): con l'etichetta «scritto dopo il congelamento», con la definizione già scritta nel piano prima dei
   risultati, fuori dall'elenco dei file con impronta (elenco A), e senza poter cambiare i due risultati principali né la frase d'apertura.
7. Regola del proprietario (16-17 novembre, «Pareto»): prima del congelamento si fa solo ciò che blocca il run o che il piano impone; il resto si
   rimanda. Il congelamento è il push del repository pubblico con l'elenco A: la data del push è la prova di data. Dopo, un cambiamento a ciò che
   entra nella misura è un run nuovo; il programma di analisi invece si può correggere se la modifica si documenta e si pubblicano le due uscite
   (PIANO, Aggiunte del 12 novembre, punto 6).

## Le tre strade
1. **Ora**: in ogni rapporto un blocco «Fuori dalla sfera (selettività)», mai nella frase d'apertura: quanti casi malevoli fuori sfera, in quanti il
   giudice scatta (a maggioranza delle sessioni), e quante sessioni; descrittivo, con la dicitura «il giudice non dichiara di coprirli». Richiede
   codice nuovo in `analisi_v3.py` (che sta nell'elenco A) e i suoi test, prima del congelamento.
2. **Definizione scritta ora nel piano, codice dopo il congelamento**: come la vista per minaccia. Il piano fissa adesso cosa si calcola e come si
   etichetta («scritto dopo il congelamento»); il codice si scrive dopo, a letture chiuse, e i verdetti fuori sfera sono già nei dati.
3. **Mai**: si scrive come limite («la selettività non è riportata») e basta.

## Raccomandazione di Claude (l'autore del codice e del piano): la strada 2
Motivi: il piano non mette la selettività in testa né la usa per la frase d'apertura, quindi non cambia i due risultati principali; è la stessa
categoria della vista per minaccia, già rinviata per la regola Pareto; i verdetti ci sono già; la definizione nel piano, fissata prima di vedere i
verdetti, impedisce di sceglierla a posteriori. Alternativa scartata: la 3, perché il piano la promette come «accanto» e farebbe sparire dall'analisi
un'intera parte del disegno del dataset (18 casi fuori sfera per AlignmentCheck nella lettura larga).
Interesse dell'autore da tenere presente: scrivere meno codice prima del congelamento.
"""

domanda = """# Cosa ti chiedo (un solo giro, rispondi in italiano, massimo 600 parole)
Il proprietario del progetto è stanco e si affida al tuo parere per decidere. Prima di ogni altra cosa, una riga: **CONCORDO**, **CONCORDO CON RISERVE**
oppure **NON CONCORDO** con la raccomandazione (strada 2). Poi:
1. **Fatti.** Quali delle affermazioni numerate nei «fatti» (1-7) il testo incollato smentisce o non permette di sostenere? Quali non puoi verificare
   (dillo, non indovinare)?
2. **Ragioni.** Perché concordi o no. Se preferisci un'altra strada (o una quarta), dì quale e perché, con il costo.
3. **Cosa manca.** Rischi o considerazioni che l'analisi non ha pesato: per esempio integrità e verificabilità (si può scegliere cosa riportare guardando i
   risultati?), cosa perde un lettore esterno se la selettività manca o arriva dopo, l'effetto del rimandare su chi pubblica i risultati.
Non ripetere l'analisi. Se non trovi niente da obiettare, dillo senza riempire.
"""

sistema = """Sei un revisore esterno di metodologia e di integrità di un esperimento. Il testo e il codice che leggi li ha scritti un altro modello (Claude)
insieme al proprietario del progetto: tu sei di un'altra famiglia e il tuo compito è dire se l'analisi che segue regge, e dove no. Non hai accesso al
repository, non hai strumenti, non puoi fare domande: hai solo il testo incollato qui sotto. Dove chiedi di verificare un fatto, cita il documento e la
riga, oppure scrivi NON VERIFICABILE. Rispondi in italiano.
"""

parti = [("ANALISI DI CLAUDE", analisi)] + [(t, x) for t, x in estratti] + [(t, x) for t, x in codice] + [("PRINCIPI DEL PROGETTO (SPIRIT.md, per intero)", spirit),
        ("LA TUA DOMANDA", domanda)]
utente = "NOTA: le sezioni seguenti sono incollate per intero, con il titolo e il percorso.\n" + "".join(f"\n\n=== {t} ===\n{x}" for t, x in parti)
(OUT / "istruzione-sistema.md").write_text(sistema, encoding="utf-8", newline="\n")
(OUT / "input-utente.md").write_text(utente, encoding="utf-8", newline="\n")
meta = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
        "parti": [{"titolo": t, "caratteri": len(x), "sha256": hashlib.sha256(x.encode("utf-8")).hexdigest()} for t, x in parti]}
(OUT / "contenuto.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(len(sistema) + len(utente), "caratteri;", [(t[:40], len(x)) for t, x in parti])
