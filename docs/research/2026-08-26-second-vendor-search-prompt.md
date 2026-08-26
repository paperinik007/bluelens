# Prompt per ricerca esterna: secondo vendor per audit indipendente di agentic threat detection

## Contesto

Abbiamo un harness di audit funzionante che:
- Prende un transcript JSON multi-turno (turni user/assistant/tool, con tool_call e risultati)
- Lo invia a un detector (containerizzato, via stdin/stdout JSON)
- Riceve un verdetto strutturato (label: malicious/benign, confidence: float, technique_detected: string, rationale: string)
- Produce metriche intento-vs-effetto, CI, tabelle per-tecnica

Abbiamo già completato un audit su `aidr` (FareedKhan-dev/agentic-threat-detection) con 31 casi.
Ora cerchiamo un **secondo vendor** per validare il metodo. Il criterio di successo è:
- Se il secondo vendor mostra lo stesso pattern ("condanna l'intento, non l'effetto"), il metodo è generale.
- Se il secondo vendor si comporta diversamente, il metodo ha distinto due detector — che è comunque una validazione.

## Cosa abbiamo già esplorato (NON rifare)

### Ricerca originale (2026-08-20)
14 vendor in-focus, 5 out-of-focus, 4 OSS self-hostabili. Documento: `docs/research/2026-08-20-vendor-market-agentic-threat-detection.md`

### Verifica completata (2026-08-26)
I 4 OSS sono già stati verificati per suitability con il nostro harness:

| Candidato | Verdetto | Motivo |
|---|---|---|
| **Invariant Labs** (`invariantlabs-ai/invariant`) | ❌ | Rule engine, non detector. Testa le nostre policy, non la logica del vendor |
| **LlamaFirewall** (`meta-llama/PurpleLlama`, `llama_firewall`) | ✅ **Migliore** | `scan_replay()` multi-turno, output `ScanResult(decision, score, reason)`. AlignmentCheck richiede API key Together (o OpenRouter con patch) |
| **AgentDoG 1.5** (`AI45Research/AgentDoG1.5-...`) | ⚠️ | GPU obbligatoria (vLLM/SGLang). Non su OpenRouter/Together. Tassonomia 3D più completa |
| **Lasso Security** (`lasso-security/mcp-gateway`) | ❌ | Gateway MCP, non detector di transcript |
| **AgentShield** (`dl-eigenart/agentshield-platform`) | ❌ | Single-turn classifier. Self-hosted non ancora disponibile |
| **Snyk Agent Scan** (`snyk/agent-scan`) | ❌ | Scanner MCP server, non detector di transcript |
| **JANUS/Vanguard** (`xiongyuaay/JANUS`) | ❌ | Codice di ricerca, non production-ready |
| **XSafeClaw** (`XSafeAI/XSafeClaw`) | ❌ | Piattaforma runtime per agenti (hook, HITL), non detector di transcript offline |
| **Cisco MCP Scanner**, **Fixer MCP Scan**, **msoedov/agentic_security**, **sentinel-ai**, **CHATS-lab** | ❌ | Scanner MCP, red-team framework, proxy, o verticali |

## Cosa serve ora (da fare)

### 1. Verificare su OpenRouter se *qualunque* modello trajectory-level è disponibile

AgentDoG 1.5 non c'è. Ma potrebbero esserci modelli trajectory-level alternativi. Cerca su OpenRouter (via API, senza chiave si può vedere il catalogo) keyword: `agentdog`, `tracesafe`, `vanguard`, `agent-safety`, `trajectory`, `guardrail`, `safety-classifier`. Includi anche Together AI e altri provider OpenAI-compatible.

### 2. Cercare modelli trajectory-level su Hugging Face

Oltre ad AgentDoG, cerca modelli specializzati in classificazione di intere traiettorie multi-turno (NON classificatori single-turn). Keyword:
- `agent trajectory safety`
- `agentic safety classification`
- `multi-turn agent guardrail`
- `tool call sequence safety`
- `agent safety diagnosis`
- `mid-trajectory safety`

Per ogni modello trovato, verifica:
- **Parametri**: quanti B? Richiede GPU?
- **Pipeline tag**: è `text-classification` o `token-classification`? (single-turn) o altro?
- **Input**: accetta un transcript JSON multi-turno o solo testo?
- **Output**: produce un verdetto strutturato (label, confidence, categoria)?
- **Tassonomia**: ha una tassonomia dichiarata di tecniche/rischi?
- **Serving**: è disponibile via API (OpenRouter, Together, HF Inference) o solo self-hosted?

### 3. Verificare se LlamaFirewall AlignmentCheck può essere puntato a OpenRouter

Abbiamo già letto il codice di `custom_check_scanner.py`:
```python
api_base_url: str = "https://api.together.xyz/v1",
api_key_env_var: str = "TOGETHER_API_KEY",
```
Il parametro è configurabile ma `AlignmentCheckScanner.__init__()` non lo espone (usa il default). Verifica:
- Se esiste una versione più recente di LlamaFirewall che espone questi parametri
- Se è possibile creare una sottoclasse di `AlignmentCheckScanner` che passa `api_base_url="https://openrouter.ai/api/v1"` e `api_key_env_var="OPENROUTER_API_KEY"` (senza modificare il codice sorgente)
- Se OpenRouter richiede header HTTP-Referer per modelli Meta (LlamaFirewall usa Llama-4-Maverick-17B-128E-Instruct-FP8 come default)

### 4. Cercare vendor non-OSS che hanno self-serve trial API

Dalla ricerca originale, la maggior parte dei vendor è contact-sales. Ma potrebbero esistere vendor con API self-serve (no demo call). Criteri:
- Accetta un transcript multi-turno con tool call (non solo singolo prompt)
- Restituisce verdetto strutturato
- Ha self-serve trial (signup, API key, no sales call)
- Prezzo: pay-as-you-go o free tier

Cerca su: best-ai-agent-security-platforms-2026, agentic security vendor list, AI agent security tools comparison. Verifica ogni candidato contro il sito ufficiale.

### 5. Verificare XSafeClaw più a fondo

Il README dice che ha un modulo "Agent Guard" per "trajectory-level & tool-call-level safety evaluation with human-in-the-loop approval". Verifica:
- Se il modulo `Agent Guard` può essere usato *offline* (dare un transcript, ricevere un verdetto) senza dover eseguire l'intera piattaforma
- Se esiste una API CLI o SDK per classificare transcript salvati
- Che output produce (label, confidence, categoria?)

### 6. Cercare nuovi candidati su GitHub

Cerca con keyword (autenticato, per avere risultati completi):
- `agent-safety`, `agent-guardrail`, `trajectory-classification`, `agent-monitor`, `tool-call-security`
- Escludi repository con < 50 stelle (salvo eccezioni)
- Per ogni repo con > 50 stelle e descrizione pertinente: leggi README, verifica input/output, tassonomia, self-hostabilità

---

## Output richiesto

Per ogni candidato che supera il primo filtro, fornisci scheda:

```
## [Nome candidato] (link)
- Input: [formato accettato, multi-turno?]
- Output: [verdetto strutturato? label/confidence/tecnica?]
- Tassonomia: [categorie dichiarate?]
- Self-hostabile: [pip install / container? GPU? API key?]
- Costo: [gratuito / pay-as-you-go / contact-sales?]
- Adapter effort: [quanto lavoro per adattare al nostro harness?]
- Verdetto: [✅ adatto / ⚠️ possibile / ❌ non adatto]
```

## Note metodologiche

- Usa fonti primarie (GitHub README, documentazione ufficiale, API docs). Non blogpost di terzi.
- Niente listicle "top 10" come fonte — usali per scoprire nomi, poi verifica su fonti primarie.
- Se un sito non è raggiungibile o non ha documentazione tecnica, segnalalo come "non verificabile".
- **L'obiettivo è trovare UN candidato adatto**, non fare una lista esaustiva. Il tempo è meglio speso su verifica approfondita di 1-2 candidati che su scoperta superficiale di 20.