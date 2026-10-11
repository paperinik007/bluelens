# Revisore alla cieca: google/gemini-3.1-pro-preview

Ecco la revisione indipendente dei tre prodotti di sicurezza, basata esclusivamente sulle dichiarazioni fornite dai produttori.

### GIUDICE 1: PromptGuard 2 (in LlamaFirewall)
**Natura del giudice:** La sua domanda riguarda il **testo** (si confronta con l'intento del test, classificando i prompt come benigni o maligni in base all'intento di sovrascrivere le istruzioni, indipendentemente dal successo o dall'azione dell'agente).

| Asse | Valore | SI/NO/DUE LETTURE | Frase esatta | File |
|---|---|---|---|---|
| **Dove legge** | Richiesta | SI | "operates on user inputs" | LlamaFirewall/README.md |
| | Contenuto | SI | "untrusted content such as web data" | LlamaFirewall/README.md |
| | Azioni dell'agente | NO | nessuna frase | - |
| | Codice degli strumenti | NO | nessuna frase | - |
| **Attacco da** | Richiesta | SI | "prompt injections originating from user inputs" | prompt-guard-2.md |
| | Contenuto | SI | "prompt injections originating from... tool outputs" | prompt-guard-2.md |
| | Strumento | NO | nessuna frase | - |
| | Agente | NO | nessuna frase | - |
| **Forme** | Iniezione camuffata | SI | "manipulate untrusted third-party and user data in the context window" | MODEL_CARD.md |
| | Override | SI | "explicitly attempts to override prior instructions" | MODEL_CARD.md |
| | Pretesto | SI | "social engineering prompts" | LlamaFirewall/README.md |
| | Diretta | SI | "detects direct prompt injection attempts" | LlamaFirewall/README.md |
| **Azioni** | Dati a chi non deve averli | NO | nessuna frase | - |
| | Rubare credenziali | NO | nessuna frase | - |
| | Alterare dati o registri | NO | nessuna frase | - |
| | Cambiare permessi o identità | NO | nessuna frase | - |
| | Restare nel sistema | NO | nessuna frase | - |
| | Distruggere o disattivare | NO | nessuna frase | - |
| | Consumare risorse | NO | nessuna frase | - |
| | Muovere denaro | NO | nessuna frase | - |
| | Usare l'agente contro terzi | NO | nessuna frase | - |
| | Ingannare chi usa l'agente | NO | nessuna frase | - |
| | Eseguire comandi o lanciare altri agenti | SI | "ensuring that malicious code is identified and mitigated before it can be executed" | prompt-guard-2.md |
| | Scoprire il sistema | NO | nessuna frase | - |

---

### GIUDICE 2: AlignmentCheck (in LlamaFirewall)
**Natura del giudice:** La sua domanda riguarda le **azioni dell'agente** (ispeziona il processo di ragionamento e le azioni in tempo reale per verificare la coerenza con l'intento dell'utente).

| Asse | Valore | SI/NO/DUE LETTURE | Frase esatta | File |
|---|---|---|---|---|
| **Dove legge** | Richiesta | SI | "comparing them to the user's stated objective" | alignment-check.md |
| | Contenuto | SI | "misleading tool output" | alignment-check.md |
| | Azioni dell'agente | SI | "inspects the reasoning process of an LLM agent in real time" | LlamaFirewall/README.md |
| | Codice degli strumenti | NO | nessuna frase | - |
| **Attacco da** | Richiesta | SI | "Agent Goal Hijacking Prompt Injections" | alignment-check.md |
| | Contenuto | SI | "jailbreaks embedded in third-party content" | alignment-check.md |
| | Strumento | NO | nessuna frase | - |
| | Agente | DUE LETTURE | *Stretta* (l'agente devia a causa di un attacco): "prompt-injection induced misalignment". *Larga* (l'agente devia da solo): "detecting signs of agent misalignment" / "detecting behavioral drift early" | LlamaFirewall/README.md / alignment-check.md |
| **Forme** | Iniezione camuffata | SI | "covert prompt injection" / "indirect injections that appear benign in isolation" | alignment-check.md |
| | Override | NO | nessuna frase | - |
| | Pretesto | NO | nessuna frase | - |
| | Diretta | SI | "application-specific prompt injections" | alignment-check.md |
| **Azioni** | Dati a chi non deve averli | NO | nessuna frase | - |
| | Rubare credenziali | NO | nessuna frase | - |
| | Alterare dati o registri | NO | nessuna frase | - |
| | Cambiare permessi o identità | NO | nessuna frase | - |
| | Restare nel sistema | NO | nessuna frase | - |
| | Distruggere o disattivare | NO | nessuna frase | - |
| | Consumare risorse | NO | nessuna frase | - |
| | Muovere denaro | NO | nessuna frase | - |
| | Usare l'agente contro terzi | NO | nessuna frase | - |
| | Ingannare chi usa l'agente | NO | nessuna frase | - |
| | Eseguire comandi o lanciare altri agenti | SI | "blocking malicious code from being executed through prompt injection" | alignment-check.md |
| | Scoprire il sistema | NO | nessuna frase | - |

---

### GIUDICE 3: aidr
**Natura del giudice:** La sua domanda riguarda le **azioni dell'agente** (ricostruisce ciò che l'agente ha fatto leggendo la trascrizione, i ragionamenti e le chiamate agli strumenti).

| Asse | Valore | SI/NO/DUE LETTURE | Frase esatta | File |
|---|---|---|---|---|
| **Dove legge** | Richiesta | SI | "the prompt it was given" | README.md |
| | Contenuto | SI | "Malicious instructions planted in data the agent reads" | threat_repository.yaml |
| | Azioni dell'agente | SI | "the tool calls it made" | README.md |
| | Codice degli strumenti | SI | "read the tool's actual source code" | README.md |
| **Attacco da** | Richiesta | SI | "The user prompt itself instructs the agent to act outside its stated task." | threat_repository.yaml |
| | Contenuto | SI | "Malicious instructions planted in data the agent reads" | threat_repository.yaml |
| | Strumento | SI | "A tool returns manipulated results that mislead the agent's reasoning" | threat_repository.yaml |
| | Agente | SI | "The agent probes for ways to act outside its isolated environment" | threat_repository.yaml |
| **Forme** | Iniezione camuffata | SI | "A request is reframed or obfuscated to slip past a safety filter" | threat_repository.yaml |
| | Override | SI | "the prompt asks the agent to disable safeguards" | threat_repository.yaml |
| | Pretesto | NO | nessuna frase | - |
| | Diretta | SI | "Direct Prompt Injection" | threat_repository.yaml |
| **Azioni** | Dati a chi non deve averli | SI | "Sensitive data is moved outside the trusted boundary" | threat_repository.yaml |
| | Rubare credenziali | SI | "Tools accessing credentials" / "real credential leakage" | sifter.py / inspector.py |
| | Alterare dati o registri | SI | "The agent deletes, overwrites, or corrupts resources" | threat_repository.yaml |
| | Cambiare permessi o identità | SI | "A tool is used to gain access or rights beyond the agent's assigned scope" | threat_repository.yaml |
| | Restare nel sistema | NO | nessuna frase | - |
| | Distruggere o disattivare | SI | "The agent deletes, overwrites, or corrupts resources" | threat_repository.yaml |
| | Consumare risorse | SI | "The agent drives operations that exhaust compute, storage, or quota" | threat_repository.yaml |
| | Muovere denaro | NO | nessuna frase | - |
| | Usare l'agente contro terzi | NO | nessuna frase | - |
| | Ingannare chi usa l'agente | NO | nessuna frase | - |
| | Eseguire comandi o lanciare altri agenti | SI | "Gain control and execute malicious actions inside the agentic environment" | threat_repository.yaml |
| | Scoprire il sistema | SI | "The agent probes for ways to act outside its isolated environment" | threat_repository.yaml |

---

### Punti più incerti emersi dalla revisione:

1. **PromptGuard 2 e le "Azioni":** Il produttore dichiara esplicitamente che il modello valuta *solo l'intento* di sovrascrivere le istruzioni ("considers only the intent... regardless of whether the prompt is potentially harmful"). Di conseguenza, quasi tutte le azioni specifiche (rubare dati, alterare registri, ecc.) risultano "NO", ad eccezione dell'esecuzione di codice maligno, che viene citata esplicitamente come rischio coperto.
2. **AlignmentCheck e l'Attacco da Agente:** C'è un'ambiguità su *chi* o *cosa* causi il disallineamento. Il testo parla di "prompt-injection induced misalignment" (suggerendo un attaccante esterno), ma usa anche termini molto ampi come "behavioral drift" e "agent misalignment", che potrebbero implicare un agente che "allucina" o sceglie autonomamente un'azione dannosa senza un attacco a monte. Per questo è stata usata la classificazione "DUE LETTURE".
3. **aidr e l'Inganno verso l'utente:** Il framework di aidr cita strumenti che nascondono comportamenti ("A tool answers the stated request and quietly attaches extra sensitive data") o che ingannano il ragionamento dell'agente ("mislead the agent's reasoning"). Tuttavia, non c'è alcuna frase che dichiari esplicitamente la protezione contro l'inganno diretto verso l'utente finale (es. l'agente che mente all'utente), motivo per cui è stato valutato come "NO".
