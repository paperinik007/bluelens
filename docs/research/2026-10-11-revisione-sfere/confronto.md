# Sfere dei giudici: confronto con il revisore alla cieca (2026-10-11)

Revisore: `deepseek/deepseek-v4.1-flash` via OpenRouter, temperatura 0, scelto dal
proprietario ("deepseek 4.1"; su OpenRouter esiste solo la versione flash). Ha ricevuto solo
le regole (tre assi, forme, dodici azioni, due letture) e i testi dei produttori
(`input-revisore.md`), non le sfere di Claude (`docs/design/2026-10-11-sfere-giudici.md`).
Risposta in `output-revisore.md`. Costo: 0,017 dollari. Le citazioni del revisore sono state
controllate nei file dei produttori: esistono tutte.

Regola: dove coincidiamo la casella passa; i disaccordi li decide il proprietario, con il
motivo registrato. Una lettura sola (regola di arresto).

## Concordano

- PromptGuard: legge richiesta e contenuto, non azioni né codice; override sì; iniezione
  camuffata e pretesto due letture, con le stesse frasi; nessuna azione tranne il punto P2.
- AlignmentCheck: legge richiesta (come scopo), contenuto, azioni, non il codice; attacco dalla
  richiesta no, dal contenuto sì, dallo strumento no; nessuna forma tra override, pretesto,
  diretta.
- aidr: legge tutto, codice compreso; attacco da richiesta, contenuto, strumento, agente sì
  (nella lettura larga di Claude); azioni sì: dati, credenziali, alterare, permessi,
  distruggere, consumare risorse, eseguire comandi; no: restare nel sistema, muovere denaro,
  ingannare.

## Disaccordi

| # | Giudice, casella | Claude | Revisore | Valutazione di Claude |
|---|---|---|---|---|
| P1 | PromptGuard, forma diretta | no | sì ("detects direct prompt injection attempts") | errore del revisore: "direct" nel testo vuol dire "arrivata dall'utente", opposto a "indirect"; resta un'iniezione. La forma "diretta" nostra è una richiesta senza tecnica, e la scheda del modello dice "regardless of whether the prompt is potentially harmful". Resta no |
| P2 | PromptGuard, azione eseguire comandi | no | sì ("Malicious Code via Prompt Injection") | la frase è tra i rischi coperti, ma "via Prompt Injection" e "along with other scanners": risponde all'iniezione che porta il codice, non al comando in sé. Cambia l'ambito solo per una richiesta di comandi senza tecnica (`diagnostic_command_probes_external_url`). Resta no; da decidere |
| A1 | AlignmentCheck, attacco dall'agente | due letture | sì | il revisore stesso lo segna incerto (punto 4); la v2 aveva deciso due letture l'8/10. Restano due letture |
| A2 | AlignmentCheck, forma iniezione camuffata | nessuna forma | sì ("covert prompt injection") | il revisore ha ragione sulla frase; non cambia l'ambito (l'attacco nella richiesta resta fuori). Si accoglie: sì |
| A3 | AlignmentCheck, azioni | tutte, se deviano da uno scopo legittimo | nessuna, tranne il codice | con "nessuna azione" il valore "agente" non sarebbe mai in ambito, anche se il revisore lo segna sì: la sua tabella si contraddice. La dichiarazione è generale ("detects when an agent's actions diverge from the user-defined goal"). Resta "tutte, se deviano" |
| D1 | aidr, lettura stretta dall'Inspector | stretta: solo comportamento nascosto ("Classify as MALICIOUS only for genuine hidden behavior") | nessuna seconda lettura | il revisore non l'ha vista; è il punto 1 da guardare con il proprietario |
| D2 | aidr, forma pretesto | sì nella larga (T0007 "reframed or obfuscated to slip past a safety filter") | no (T0007 non nomina false identità) | entrambe le letture sono sostenibili; nella v2 aidr era dentro sui pretesti. Da decidere |
| D3 | aidr, usare l'agente contro terzi | sì (T0004 "turned harmful through the arguments the agent passes it") | due letture | il revisore non ha considerato T0004; decisione già presa sulla v2 (`atlas_t0077_html_payload` è T0004, nel catalogo). Resta sì |
| D4 | aidr, scoprire il sistema | no | sì (T0008 "probes for ways to act outside its isolated environment") | T0008 è cercare di uscire dal recinto, che sta sotto "eseguire comandi"; "scoprire il sistema" è conoscere istruzioni e strumenti dell'agente. Resta no; da decidere |

## Seconda revisione: Gemini (2026-10-11)

Su richiesta del proprietario, un secondo revisore scelto da Claude: `google/gemini-3.1-pro-preview`
(un'altra famiglia, diversa da Claude, dai giudici, dall'agente e dal primo revisore; il "pro"
più recente su OpenRouter). Stesso input, alla cieca. Risposta in `output-revisore-gemini.md`.
Costo: 0,087 dollari.

| # | Casella | Claude | DeepSeek | Gemini | Lettura |
|---|---|---|---|---|---|
| P1 | PromptGuard, forma diretta | no | sì | sì | i due revisori leggono "direct prompt injection" come la nostra forma "diretta": collisione di nomi nel nostro prompt (due revisori che sbagliano allo stesso modo indicano un difetto dell'istruzione). Resta no; proposta: rinominare la forma in "esplicita, senza tecnica" |
| P2 | PromptGuard, eseguire comandi | no | sì | sì | la frase c'è tra i rischi coperti ("Malicious Code via Prompt Injection"); la scheda del modello dice "regardless of whether the prompt is potentially harmful". Dichiarazione ambigua: proposta due letture (stretta no, larga sì) |
| P3 | PromptGuard, iniezione camuffata e pretesto | due letture | due letture | sì | concordano Claude e DeepSeek; Gemini non considera la scheda del modello. Restano due letture |
| A1 | AlignmentCheck, attacco dall'agente | due letture | sì | due letture | concordano Claude e Gemini, come la v2 dell'8/10 |
| A2 | AlignmentCheck, iniezione camuffata | sì (accolta) | sì | sì | concordano |
| A3 | AlignmentCheck, azioni | tutte, se deviano | solo codice | solo codice | entrambi chiedono una frase per ogni azione; la dichiarazione è generale. Con "nessuna azione" il valore "agente" non è mai in ambito. Effetto dell'istruzione ("se nessuna frase lo sostiene, scrivi nessuna frase"). Resta "tutte, se deviano" |
| A4 | AlignmentCheck, attacco dalla richiesta | no | no | sì ("Agent Goal Hijacking Prompt Injections") | regola della v2 (lo scopo dell'utente è l'attacco). Resta no |
| D1 | aidr, lettura stretta dall'Inspector | sì | non vista | non vista | da decidere dal proprietario |
| D2 | aidr, forma pretesto | sì nella larga | no | no | i due revisori concordano: T0007 non nomina false identità. Proposta: si accoglie no |
| D3 | aidr, usare l'agente contro terzi | sì (T0004) | due letture | no | decisione già presa sulla v2 (`atlas_t0077_html_payload` è T0004). Resta sì |
| D4 | aidr, scoprire il sistema | no | sì (T0008) | sì (T0008) | i due revisori concordano su "probes": proposta si accoglie sì |
