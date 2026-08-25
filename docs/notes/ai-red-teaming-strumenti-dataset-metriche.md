# AI Red Teaming e validazione di detector LLM — strumenti, dataset, metriche

Data: 2026-08-25. Sintesi da una conversazione esplorativa su strumenti e metodi per
testare la sicurezza dei modelli di linguaggio. Rilevante per `agentic-security-audits`:
il progetto misura detector di minacce agentiche come ente indipendente — questo
materiale mappa il mercato degli strumenti, i dataset di attacco e le metriche di
validazione (SLA) che un misuratore indipendente deve conoscere per posizionarsi.

---

## 1. Strumenti di red teaming (l'open source domina)

| Strumento | Licenza | Costo | Capacità principali |
|---|---|---|---|
| **Garak** | Apache 2.0 | Gratuito | Vulnerability scanner puro: migliaia di probe noti per allucinazioni, tossicità, jailbreak. Zero codice per iniziare. |
| **PyRIT** (Microsoft) | MIT | Gratuito | Framework per scalare e automatizzare attacchi complessi contro GenAI. Per ricercatori. |
| **Promptfoo** | MIT | Gratuito | Standard per CI/CD: testa i rischi a ogni aggiornamento del modello (acquisito da OpenAI, 2025). |
| **Giskard** | Core OSS / Enterprise | Gratuito+ | Robustezza + reportistica di conformità, soprattutto EU AI Act. |
| **NeMo Guardrails** | OSS | Gratuito | Non un tester ma un sistema di difesa: impone guardrails per evitare uscite dal percorso predefinito. |

Alternative commerciali (cruscotti + monitoraggio continuo): Mindgard, Kosmoy, Cisco AI
Defense — da migliaia a decine di migliaia di €/anno.

**Come scegliere**: sviluppatore → Promptfoo (CI/CD); check-up immediato → Garak
(libreria di probe pronta); conformità EU → Giskard/Kosmoy.

---

## 2. Standard di riferimento

- **OWASP** — Top 10 for LLM + AI Testing Guide (nov 2025): framework di riferimento universale.
- **NIST** (programma ARIA) — metriche governative per impatti e rischi.
- **MITRE ATLAS** — matrice delle tattiche reali usate dagli attaccanti contro sistemi IA.

---

## 3. Dataset di attacco (Hugging Face)

| Dataset | Cosa offre |
|---|---|
| **JailbreakBench** (JBB-Behaviors) | Comportamenti dannosi e benigni, categorizzati per policy dei modelli commerciali |
| **HarmBench** | Red teaming automatizzato, test pre-calcolati per decine di modelli |
| **Dataset aggregati** (es. Necent) | 30+ fonti combinate, etichette per categoria (obfuscation, toxicity, prompt_injection) |
| **AdvBench / Do-Not-Answer** | Istruzioni dannose + domande a cui un'IA sicura deve sempre rifiutarsi |

Recupero via libreria `datasets` (Hugging Face) o librerie dedicate (es. `jailbreakbench`)
— poche righe di Python, niente download manuali.

---

## 4. Architettura della sandbox (4 stadi in sequenza)

```
Dataset di attacco → Detector sotto test → LLM Bersaglio → LLM Giudice
```

1. **Attaccante** (dataset): lo script pesca un prompt malevolo.
2. **Difensore** (il tool sotto test): se blocca → "successo difensivo"; se non lo vede → passa.
3. **Bersaglio** (LLM): il prompt non intercettato colpisce un modello di base (Llama locale o API GPT).
4. **Giudice** (LLM-as-a-judge): un secondo modello (es. Jailjudge) valuta se la risposta
   asseconda la richiesta dannosa → determina se il detector ha fallito.

Il ciclo si ripete migliaia di volte per produrre: % attacchi bloccati, % falliti, % falsi positivi.

---

## 5. Metriche di validazione (prospettiva black-box)

Per chi valida il detector, il tool è una scatola nera: contano solo le metriche.

- **Trade-off TPR/FPR**: TPR a parità di FPR desiderato.
- **Curva ROC / AUC**: capacità discriminativa globale.
- **Funzione di costo**: bilancia danno di un attacco vs blocco di un utente legittimo.
- **Generalizzazione (OOD)** e **latenza**: efficacia su vettori inediti + impatto sui tempi di risposta.

---

## 6. Soglie SLA per contesto operativo

| Contesto d'uso | FPR target | TPR target | Priorità operativa |
|---|---|---|---|
| SaaS consumer / mass market | < 0,1% – 0,5% | 80% – 85% | Massima usabilità: bloccare utenti reali → abbandoni immediati |
| Enterprise / B2B standard | < 1,0% | 85% – 90% | Bilancio protezione dati / produttività |
| Alto rischio (finanza, sanità, difesa) | < 2,0% – 5,0% | > 95% | Massima sicurezza: il costo della violazione supera il disagio |

**Criteri di validazione delle soglie:**
- **Metodo del punto fisso**: si fissa l'FPR massimo ammesso dal business (es. 0,5%) e si misura il TPR in quel punto di cutoff della ROC.
- **Differenziazione per categoria**: direct prompt injection → SLA severi (TPR > 95%); jailbreak sfumati/roleplay → soglie più basse (~80%) per non sacrificare la creatività.
- **Integrazione con la mitigazione**: hard block → FPR < 0,1%; soft mitigation (sanitizzazione/prompt difensivi) → FPR ~2-3% tollerato.

---

## 7. Complessità note

- **Obsolescenza rapida dei dataset** noti.
- **Errori di valutazione dell'LLM giudice**.
- **Attacchi multi-turn** articolati su più passaggi.

---

## Rilevanza per questo progetto

Il progetto misura detector di minacce agentiche (non di prompt injection su chat). Le
differenze chiave da tenere presenti:

1. **L'oggetto misurato è diverso**: qui il detector valuta *comportamenti* di un agente
   (tool call, sequenze), non risposte testuali. La pipeline "dataset → detector → target
   → giudice" resta valida come forma, ma il "giudice" per un detector agentico è la
   verifica di un esito su stato del mondo, non un LLM-as-judge su testo.
2. **Le metriche coincidono**: TPR/FPR, ROC/AUC, funzione di costo, generalizzazione OOD —
   sono esattamente ciò che `metrics.py` calcola già (precision/recall/F1 + confidenza).
3. **Gli SLA di riferimento** (§6) sono il benchmark esterno con cui confrontare i numeri
   dichiarati dai vendor — coerente con SPIRIT.md principio 3 (onestà statistica).
4. **I dataset di attacco** (§3) sono una fonte potenziale per Plan 6 (espansione del
   dataset di casi), con la cautela che sono tarati su chat LLM, non su agenti con tool.
