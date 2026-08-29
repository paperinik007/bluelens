# Esiste un agente/container "bersaglio" standardizzato per testare detector agentici di terze parti?

> **Ricerca**: 2026-08-29. Verifica con fonti primarie (GitHub API, README raw, siti vendor).
> Tag: `[VERIFICATO, fonte]` per ogni affermazione; `[NON VERIFICATO]` per le mancanze.

---

## Conclusione (TL;DR)

**Parzialmente — e il "parzialmente" è fragile.**

Esistono **due progetti recenti** che rispondono esattamente alla domanda di ricerca (agente deliberatamente vulnerabile, containerizzato, pensato per essere attaccato — non un benchmark di robustezza dell'agente):

1. **`Tcotl/DVLAA`** — *Damn Vulnerable LLM and Agent Application*. Locale, OWASP LLM Top 10 + Agent Security Top 10, **Docker-first** (one-click install), push 2026-08-27 (2 giorni fa), bilingue. [VERIFICATO, https://github.com/Tcotl/DVLAA]
2. **`viralvaghela/LLM-Agent-CTF`** (*Damn Vulnerable Agentic AI*, DVAA) — applicazione customer-support deliberatamente vulnerabile (FastAPI + LangChain + LangGraph + Ollama), con **due build affiancate** (`WithoutGuardrail/` baseline vulnerabile + `WithGuardrail/` con difese ingenui bypass-abili) mappate a OWASP ASI Top 10 — strutturalmente analogo al pattern "bersaglio + vendor mediocre" che servirebbe a BlueLens. Push 2026-05-28 (3 mesi esatti). [VERIFICATO, https://github.com/viralvaghela/LLM-Agent-CTF]

**Nessuno dei due è immediatamente riusabile per questo progetto**, ma per ragioni diverse:

- **DVLAA**: ha *tutto* (Docker, freschezza, tassonomia) **tranne** la licenza — campo `license: null` nella GitHub API. Per lo standard di questo progetto (vedi `docs/research/2026-08-20-vendor-market-agentic-threat-detection.md`, sezione "Suitability for the Fase 1 harness" → "Maintenance / license": nessuna licenza = scartato), è **momentaneamente fuori**. [VERIFICATO, https://api.github.com/repos/Tcotl/DVLAA]
- **DVAA**: licenza assente anch'essa **e** push a 3 mesi esatti = soglia del progetto. Stesso motivo di scarto, doppio. Inoltre dipende da Ollama + `llama3.1`/`granite3.1-moe` locale, vincolo di deployment non banale. [VERIFICATO, https://api.github.com/repos/viralvaghela/LLM-Agent-CTF + README]

**Esiste anche un terzo progetto storico, `ReversecLabs/damn-vulnerable-llm-agent` (DVLA)**, ma è **stale da 14 mesi** (push 2025-06-25) e ha fork residui che puntano ancora a `WithSecureLabs`. Scartato per manutenzione, nonostante licenza Apache-2.0. [VERIFICATO, https://api.github.com/repos/ReversecLabs/damn-vulnerable-llm-agent]

Il progetto **non è quindi "pronto da importare"**, ma esiste ed è in crescita: i due candidati freschi hanno 17+8 stelle e una struttura corretta. La decisione di BlueLens di costruirsi il proprio toy agent (in `src/toy_agent/`) resta **solida e non duplica sforzo altrui**: non esiste un bersaglio open-source, mantenuto, licenziato e pronto all'uso per il caso d'uso specifico di BlueLens.

---

## Cosa è stato cercato (e cosa è stato escluso in partenza)

La domanda di ricerca distingue due categorie:

| Categoria | Esempi NOTI (già esclusi in altri doc del progetto) |
|---|---|
| **Benchmark di attacchi** (misurano la robustezza dell'agente stesso) | R-Judge, InjecAgent, AgentDojo, AgentHarm, ToolEmu, AgentBench, ASB, TraceSafe, AgentAuditor/ASSEBench — *vedi `docs/research/2026-08-19-prior-art-agent-security-harnesses.md`* |
| **Framework attacker / scanner di LLM** (non spediscono un agente bersaglio) | PyRIT, Garak, MAESTRO, prompt-injection scanners standalone |
| **Harness bersaglio per detector** (oggetto della ricerca) | DVLA, DVLAA, DVAA, Damn-Vulnerable-MCP-Server e simili |

Solo l'ultima categoria è in scope. Le altre due non sono state ri-verificate — è esplicito nella richiesta.

---

## Verifica punto 1 — "Damn Vulnerable MCP Server" e simili

Esistono almeno **tre** progetti in questo pattern, tutti focalizzati sul **server MCP vulnerabile** (non sull'agente che usa l'MCP). Sono quasi tutti CTF-style.

### 1.1 `harishsg993010/damn-vulnerable-MCP-server` (DVMCP)

| Campo | Valore | Fonte |
|---|---|---|
| Descrizione | "Damn Vulnerable Model Context Protocol (MCP) — A deliberately vulnerable implementation of the Model Context Protocol (MCP) for educational purposes." 10 challenge graduati (easy/medium/hard). | [VERIFICATO, https://github.com/harishsg993010/damn-vulnerable-MCP-server] |
| Licenza | `null` (non dichiarata) | [VERIFICATO, https://api.github.com/repos/harishsg993010/damn-vulnerable-MCP-server] |
| Ultimo push | **2025-12-08** (≈ 9 mesi fa) | [VERIFICATO, GitHub API] |
| Stelle | 1.341 | [VERIFICATO, GitHub API] |
| Containerizzato | Sì — `Dockerfile` alla root, `docker build -t dvmcp . && docker run -p 9001-9010:9001-9010 dvmcp`, `docker-setup.md` di accompagnamento | [VERIFICATO, README] |
| È un agente? | **No** — è un server MCP vulnerabile, non un agente. Le challenge sono: prompt injection lato tool, tool poisoning, eccesso di permessi, rug pulls, tool shadowing, indiretta, token theft, code execution, remote access, multi-vector. | [VERIFICATO, README + solutions/] |
| Pensato per detector di terze parti? | **No** — esplicitamente CTF-style ("educational, graded challenges, solution guides"). | [VERIFICATO, README + `solutions/challenge*_solution.md`] |

**Verdetto**: **SCARTATO**. Ragione: doppio — licenza assente + push > 3 mesi. *Nota architetturale*: inoltre non è un agente — è un server MCP, e BlueLens non testa detection MCP-server-side (testa traiettorie di tool-call lato LLM). Quindi anche se fosse aggiornato, sarebbe la categoria sbagliata.

### 1.2 Altri "MCP vulnerable" trovati

La ricerca `q=MCP+vulnerable+CTF` su GitHub ha restituito 3 entry aggiuntive non meglio identificate (nomi non leggibili dallo snippet):
- "Repo with intentionally vulnerable MCP servers for a CTF style learning experience"
- "Intentionally vulnerable MCP server for security research, CTF challenges, and education — featuring 20+ exploits across path traversal, …"
- "Deliberately vulnerable MCP server for security training — 26 challenges across 4 difficulty levels (incl. a secure reference), a victim-…"

Tutti e 3 sembrano essere server MCP, non agenti, e probabilmente CTF-style. [NON VERIFICATO oltre lo snippet — servirebbe drill-down]

---

## Verifica punto 2 — Garak (NVIDIA) e PyRIT (Microsoft)

### 2.1 NVIDIA Garak

| Campo | Valore | Fonte |
|---|---|---|
| Descrizione | "garak, LLM vulnerability scanner" — Generative AI Red-teaming & Assessment Kit. Probe statici/dinamici/adattivi contro LLM esterni. | [VERIFICATO, https://github.com/NVIDIA/garak] |
| Licenza | Apache-2.0 | [VERIFICATO, GitHub API] |
| Ultimo push | **2026-08-25** (4 giorni fa) | [VERIFICATO, GitHub API] |
| Stelle | 9.070 | [VERIFICATO, GitHub API] |
| Containerizzato | Non trovato README; installazione via `pip` o `conda` | [NON VERIFICATO oltre README — possibile Docker non documentato] |
| È un agente bersaglio? | **No** — è uno *scanner*; l'utente gli punta un LLM/API esterno (`--target_type openai`, `huggingface`, `rest`, `nim`, `replicate`, `litellm`, ecc.). | [VERIFICATO, README "Intro to generators"] |
| Estensioni agentiche | Sì — `docs/source/probes/agent_breaker.rst` e `docs/source/detectors/agent_breaker.rst` esistono (probe/detector per sistemi agentici). Sono **moduli di test**, non un target. | [VERIFICATO, https://github.com/NVIDIA/garak/tree/main/docs/source] |

**Verdetto**: **non applicabile** — è uno scanner, non un bersaglio. È il tipo sbagliato di progetto per la domanda di ricerca, anche se molto utile in altri contesti.

### 2.2 Microsoft PyRIT

| Campo | Valore | Fonte |
|---|---|---|
| Descrizione | "The Python Risk Identification Tool for generative AI (PyRIT) is an open source framework built to empower security professionals and engineers to proactively identify risks in generative AI systems." | [VERIFICATO, https://github.com/microsoft/PyRIT] |
| Licenza | MIT | [VERIFICATO, GitHub API] |
| Ultimo push | **2026-08-28** (1 giorno fa) | [VERIFICATO, GitHub API] |
| Stelle | 4.375 | [VERIFICATO, GitHub API] |
| Componenti confermati | `attacks`, `targets`, `converters`, `scorers`, `datasets`, `models`, `scenarios`, `setup-techniques`, `database`, `frontend` — e un `executor` subsystem (single-turn, multi-turn, attack_configuration, compound, workflow) | [VERIFICATO, `.github/instructions/*.instructions.md`] |
| È un agente bersaglio? | **No** — i `PromptTarget` documentati sono wrapper di sistemi esterni: OpenAIChatTarget, OpenAIImageTarget, HTTPTarget, AzureBlobStorageTarget, OpenAIVideoTarget, OpenAITTSTarget, WebSocketTarget. *Definizione data dal progetto stesso*: "a generic place to send a prompt... Everything you send a prompt to is a `PromptTarget`." | [VERIFICATO, `pyrit/prompt_target/0_prompt_targets.md`] |
| Demo reference target | Il README cita assets `gandalf-demo-setup.png` / `gandalf-home-level-1.png` — Gandalf è un *target* classico, ma è un endpoint LLM giocattolo (sentence-completion con regole), non un agente con tool-call. | [VERIFICATO, presenza assets + interpretazione public] |

**Verdetto**: **non applicabile** per la domanda di ricerca — PyRIT è un attacker framework/orchestrator. *Per completezza*: la documentazione stessa esclude esplicitamente la presenza di un reference vulnerable agent target ("No reference vulnerable agent target is mentioned in this document"). [VERIFICATO, `0_prompt_targets.md`]

---

## Verifica punto 3 — OWASP GenAI Security Project

### 3.1 OWASP Top 10 for LLM Applications (legacy + corrente)

| Campo | Valore | Fonte |
|---|---|---|
| Repo legacy | `OWASP/www-project-top-10-for-large-language-model-applications` — ora redirect/archive | [VERIFICATO, https://github.com/OWASP/www-project-top-10-for-large-language-model-applications] |
| Repo attivo | `GenAI-Security-Project/GenAI-LLM-Top10` — current release **OWASP GenAI LLM Top 10 2026**, pubblicata 2026-08-04 | [VERIFICATO, https://github.com/GenAI-Security-Project/GenAI-LLM-Top10] |
| Licenza | CC BY-SA 4.0 | [VERIFICATO, badge + sezione LICENSE in entrambi i repo] |
| Containerizzato? | **No** — solo Markdown delle voci LLM01–LLM10, framework-mapping JSON, diagrammi di threat-modeling, traduzioni, script di release Zenodo | [VERIFICATO, file listing] |
| È un agente bersaglio? | **No** — è un threat taxonomy + guidance document. Nessun codice eseguibile, nessun testbed. | [VERIFICATO, descrizione repo + file listing] |

### 3.2 OWASP Agentic Security Initiative (ASI)

| Campo | Valore | Fonte |
|---|---|---|
| URL | https://genai.owasp.org/agentic-ai-threats-and-mitigations/ | [VERIFICATO] |
| Contenuto | Threat-model-based reference document — "the first in a series of guides from the OWASP Agentic Security Initiative (ASI)". Mitigations discusse a livello architetturale. | [VERIFICATO, pagina] |
| È un agente bersaglio? | **No** — è documentazione, nessun testbed eseguibile | [VERIFICATO, pagina] |
| Licenza | Non dichiarata sulla pagina; OWASP di norma usa CC BY-SA ma non verificato qui | [NON VERIFICATO] |

**Verdetto**: **non applicabile** — OWASP produce tassonomie, non agenti bersaglio.

---

## Verifica punto 4 — Meta Purple Llama / CyberSecEval

| Campo | Valore | Fonte |
|---|---|---|
| Repo | `meta-llama/PurpleLlama` — "Set of tools to assess and improve LLM security." | [VERIFICATO, https://github.com/meta-llama/PurpleLlama] |
| Licenza | `Other` (SPDX `NOASSERTION`) — components hanno licenze proprie (LlamaFirewall = MIT) | [VERIFICATO, GitHub API] |
| Ultimo push | 2026-08-18 (11 giorni fa) | [VERIFICATO, GitHub API] |
| Stelle | 4.369 | [VERIFICATO, GitHub API] |
| Componenti di CyberSecEval | `CybersecurityBenchmarks/benchmark/` contiene `autonomous_uplift_benchmark.py`, `autopatching_benchmark.py`, `canary_exploit_benchmark.py`, `instruct_or_autocomplete_benchmark.py`, `interpreter_benchmark.py`, `mitre_benchmark.py`, `mitre_frr_benchmark.py`, `multiturn_phishing_benchmark.py`, `prompt_injection_benchmark.py`, `visual_prompt_injection_benchmark.py`. | [VERIFICATO, https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks/benchmark] |
| C'è un agente vulnerabile bersaglio? | L'unico sospetto era `autopatch/` (subdirectory di `benchmark/`) | [VERIFICATO, file listing] |
| Verifica contenuto `autopatch/` | Contiene `patch_generator.py`, `report.py`, `llm_interface.py`, `prompts.py`, `crash_native.py`, `fix_examples/`, `tools.py`, `types.py`. **È un benchmark che misura la qualità delle patch generate da un LLM** — non un agente attaccabile. | [VERIFICATO, https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks/benchmark/autopatch] |
| CyberSecEval v3 agent tests | Il README cita "autonomous offensive cyber operations tests" come parte di v3 — ma sono test sul LLM (offensive capability / propensity), non agenti bersaglio. | [VERIFICATO, PurpleLlama README] |

**Verdetto**: **non applicabile** — CyberSecEval è una famiglia di benchmark LLM-level, non un agent target runnable.

---

## Verifica punto 5 — Altri progetti pertinenti (Damn-Vulnerable-Agent family)

La ricerca `q=damn+vulnerable+agent` su GitHub ha prodotto 3 match semanticamente in scope, di cui 2 verificati in profondità:

### 5.1 `Tcotl/DVLAA` (Damn Vulnerable LLM and Agent Application)

| Campo | Valore | Fonte |
|---|---|---|
| Descrizione | "DVLAA is a local LLM and Agent security range for OWASP LLM Top 10 and Agent security training." Bilingue cinese/inglese (README principale in cinese). | [VERIFICATO, https://github.com/Tcotl/DVLAA] |
| Licenza | **`null`** (non dichiarata nella GitHub API) | [VERIFICATO, https://api.github.com/repos/Tcotl/DVLAA] |
| Ultimo push | **2026-08-27** (2 giorni fa) | [VERIFICATO, GitHub API] |
| Stelle | 17 | [VERIFICATO, GitHub API] |
| Containerizzato | **Sì** — badge `Docker-Supported`, `./install.sh` one-click (auto-build image, container `dvlaa-console`, volume `dvlaa-data`, healthcheck), manual `docker build` + `docker run` documentati | [VERIFICATO, README] |
| Tassonomia | **OWASP LLM Top 10** (24 sub-challenge) + **Agent Security Top 10** (10 scenari) + **AWDP** (attack-with-defense) con CVE reali: CVE-2024-10252, CVE-2024-53450, CVE-2024-48061, CVE-2024-8181, CVE-2025-32790, CVE-2024-30256, CVE-2025-0185, CVE-2025-25282, CVE-2025-52554 | [VERIFICATO, README] |
| È un agente bersaglio? | **Sì** — explicitly "靶场" (range/target): 24 LLM + 10 Agent + 11 comprehensive + 10 AWDP challenges; AWDP include "S-Spring 客服 Agent" (servizio clienti, **identico al pattern BlueLens**). | [VERIFICATO, README] |
| Pensato per testare detector di terze parti? | **Parzialmente** — è un "range" generale per security testing/training/defense-validation. Non cita esplicitamente "third-party detector testing", ma strutturalmente l'AWDP track ("attack-with-defense" + reference implementation difese ingenui) è il pattern giusto. | [VERIFICATO per assenza; interpretato da struttura] |
| Setup requirements | Python 3.11+, opzionale SiliconFlow API key o Ollama locale; admin user/pass opzionali | [VERIFICATO, README] |

**Verdetto**: **SCARTATO per licenza assente**, nonostante tutto il resto sia perfetto. Se l'autore aggiungesse una LICENSE (Apache-2.0 o MIT), diverrebbe il candidato #1 per questo progetto. [VERIFICATO, GitHub API campo `license: null`]

### 5.2 `viralvaghela/LLM-Agent-CTF` (Damn Vulnerable Agentic AI, DVAA)

| Campo | Valore | Fonte |
|---|---|---|
| Descrizione | "Damn Vulnerable Agentic AI (DVAA) - An interactive playground for exploiting and mitigating the OWASP ASI Top 10." Customer Support app deliberatamente vulnerabile. | [VERIFICATO, https://github.com/viralvaghela/LLM-Agent-CTF] |
| Stack | FastAPI + LangChain + LangGraph + Ollama (`llama3.1` o `granite3.1-moe`) + SQLite + web chat UI su `http://localhost:8000` | [VERIFICATO, README] |
| Licenza | **Non trovata** (nessuna sezione LICENSE, nessun file LICENSE referenziato, nessun SPDX) | [VERIFICATO, README] |
| Ultimo push | **2026-05-28** (3 mesi esatti) | [VERIFICATO, GitHub API] |
| Stelle | 8 | [VERIFICATO, GitHub API] |
| Containerizzato | Non documentato nel README; serve Ollama locale con modello scaricato | [VERIFICATO, README; NON VERIFICATO presenza Dockerfile] |
| Tassonomia | **OWASP ASI Top 10** (ASI-02 Tool Misuse, ASI-03 Identity/Privilege Abuse, ASI-04 Supply Chain, ASI-06 Memory/Context Poisoning, ASI-07 Insecure Inter-Agent Comm) | [VERIFICATO, README] |
| Struttura | **Due build affiancate**: `WithoutGuardrail/` (baseline vulnerabile) + `WithGuardrail/` (stessa app + difese ingenui + bypass documentati). Il secondo è **letteralmente un vendor mediocre pronto all'uso** — il pattern ideale per testare detector di terze parti. | [VERIFICATO, README] |
| PoC exploit | Ogni challenge ha un `exploits/` directory (es. `exploit_asi02.py`, `exploit_asi04.py`, `exploit_asi06.py`, `exploit_asi07.py`) + screenshot PoC + `REPORT.md` | [VERIFICATO, README] |

**Verdetto**: **SCARTATO doppio** — licenza assente + push a 3 mesi esatti (= soglia del progetto). *Nota positiva*: la struttura `WithoutGuardrail`/`WithGuardrail` è esattamente il pattern di cui BlueLens avrebbe bisogno se mai decidesse di importare un bersaglio di terze parti invece di costruirselo. [VERIFICATO]

### 5.3 `ReversecLabs/damn-vulnerable-llm-agent` (DVLA)

| Campo | Valore | Fonte |
|---|---|---|
| Descrizione | "A sample chatbot powered by an LLM ReAct agent (Langchain) designed as an educational tool for experimenting with prompt injection attacks in ReAct agents, particularly Thought/Action/Observation injection." Adattamento di un challenge WithSecure Labs del BSides London 2023 CTF. | [VERIFICATO, https://github.com/ReversecLabs/damn-vulnerable-llm-agent] |
| Licenza | Apache-2.0 | [VERIFICATO, GitHub API] |
| Ultimo push | **2025-06-25** (14 mesi fa) | [VERIFICATO, GitHub API] |
| Stelle | 510 | [VERIFICATO, GitHub API] |
| Containerizzato | Sì — `docker build -t dvla .` documentato, ma richiede OpenAI/HF/Ollama key | [VERIFICATO, README] |
| È un agente bersaglio? | **Sì** — chatbot deliberatamente vulnerabile con tool `GetCurrentUser` e `GetUserTransactions`, due flag (leak transazioni userId=2 + UNION SQLi per estrarre password) | [VERIFICATO, README] |
| Segnali di abbandono | README contiene ancora URL `WithSecureLabs` (il fork a ReversecLabs non è stato completamente ripulito) | [VERIFICATO, README] |

**Verdetto**: **SCARTATO per mancata manutenzione** (14 mesi), nonostante licenza OK. Riferimento storico utile ma non importabile. [VERIFICATO]

---

## Riepilogo decisionale

| Progetto | Bersaglio agente? | Containerizzato? | Licenza | Freshness | Verdetto |
|---|---|---|---|---|---|
| `Tcotl/DVLAA` | ✅ Sì (range bilingue OWASP) | ✅ Sì (Docker-first) | ❌ assente | ✅ 2gg | **SCARTATO** per licenza |
| `viralvaghela/LLM-Agent-CTF` | ✅ Sì (customer-support, 2 build) | ⚠️ non documentato | ❌ assente | ⚠️ 3 mesi (soglia) | **SCARTATO** doppio |
| `ReversecLabs/damn-vulnerable-llm-agent` | ✅ Sì (ReAct agent) | ✅ Sì | ✅ Apache-2.0 | ❌ 14 mesi | **SCARTATO** per manutenzione |
| `harishsg993010/damn-vulnerable-MCP-server` | ❌ (server MCP, non agente) | ✅ Sì | ❌ assente | ❌ 9 mesi | **SCARTATO**, doppio |
| `NVIDIA/garak` | ❌ (scanner) | n/a | ✅ Apache-2.0 | ✅ 4gg | non in scope |
| `microsoft/PyRIT` | ❌ (attacker framework) | n/a | ✅ MIT | ✅ 1gg | non in scope |
| OWASP LLM Top 10 / ASI | ❌ (tassonomie) | n/a | ✅ CC BY-SA 4.0 | n/a | non in scope |
| `meta-llama/PurpleLlama` / CyberSecEval | ❌ (benchmark LLM-level) | n/a | ✅ varies | ✅ 11gg | non in scope |

---

## Implicazione per BlueLens

La decisione del progetto di **costruirsi il proprio toy agent** (`src/toy_agent/`, 6 tool su dominio servizio clienti) resta valida e non duplica sforzo altrui:

1. **Non esiste oggi un bersaglio agente open-source, mantenuto, licenziato e pronto all'uso** che copra il caso d'uso specifico di BlueLens (traiettoria di tool-call in dominio servizio clienti con 6 tool realistici).
2. I 2-3 progetti semanticamente in scope esistono e crescono (DVLAA 2gg, DVAA 3 mesi, DVLA storico) — ma sono tutti bloccati da licenza assente o freschezza insufficiente secondo lo standard del progetto.
3. DVAA (`viralvaghela/LLM-Agent-CTF`) è **strutturalmente il candidato ideale** (customer-support domain match, struttura `WithoutGuardrail`/`WithGuardrail` = letteralmente un "vendor mediocre" pronto per essere sostituito da un detector di terze parti). Se l'autore pubblicasse una LICENSE, sarebbe un candidato da riconsiderare in futuro.

Per il presente audit (aidr + LlamaFirewall + eventuale terzo vendor), il toy agent di BlueLens rimane il bersaglio corretto e metodologicamente giustificato.

---

## Fonti primarie citate

- GitHub REST API: `https://api.github.com/repos/<owner>/<repo>` per ciascun repo verificato.
- README raw: `https://raw.githubusercontent.com/<owner>/<repo>/main/README.md` per DVLAA e DVAA.
- PyRIT targets doc: `https://github.com/microsoft/PyRIT/blob/main/doc/code/targets/0_prompt_targets.md`.
- OWASP GenAI: `https://github.com/GenAI-Security-Project/GenAI-LLM-Top10` + `https://genai.owasp.org/agentic-ai-threats-and-mitigations/`.
- PurpleLlama/CyberSecEval: `https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks/benchmark` + `.../benchmark/autopatch`.

## Fonti NON verificate (gap di trasparenza)

- I 3 snippet di repo MCP-vulnerabili aggiuntivi restituiti dalla search `q=MCP+vulnerable+CTF` (nomi non leggibili) — non identificati per nome esatto.
- Presenza/assenza di Dockerfile in `viralvaghela/LLM-Agent-CTF` (README non lo cita).
- Licenza esplicita di `https://genai.owasp.org/agentic-ai-threats-and-mitigations/` (la pagina OWASP ASI non la dichiara).
