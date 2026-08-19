# Plan 5 (dataset): terreno preparatorio — benchmark esterni, schema vs contenuto, tool

Non un design doc formale — terreno preparatorio da riusare quando si scrive davvero il
design doc di Plan 5 (previsto esplicitamente da `SPIRIT.md`: "Il design tecnico del toy
agent e del dataset di attacchi verrà trattato come design doc separato"). Emerso in una
sessione successiva al merge di Gap 14/15, discutendo cosa serve per il primo risultato
reale di misura.

## Cosa manca oggi per un primo risultato reale

Non la sequenza (Gap 14/15, già risolta nel codice) — `run_batch.py` genera già da solo
`open`/`command`/`close` dal dataset, nessuna sequenza va scritta a mano per il caso
comune. Manca **solo il dataset**: nessuna directory con `TestCase` YAML esiste nel repo
oggi. L'ambiente è già pronto (immagini Docker già costruite, `.env` con le variabili
popolate) — il dataset è l'unico pezzo mancante tra oggi e un primo report reale.

## Benchmark esterni trovati (ricerca web, 2026-08-19)

Esistono benchmark accademici indipendenti per attacchi su agenti tool-use, verificati
con ricerca live (non solo memoria di training, che rischiava di essere datata su nomi e
stato attuale):

- **InjecAgent** (Zhan et al., 2024) — 1.054 casi di test, 17 tool utente + 62 tool
  attaccante, scenari di danno diretto e furto dati.
- **AgentDojo** (Debenedetti et al., NeurIPS 2024) — 97 task realistici + 629 casi di
  test di sicurezza, 4 domini (Workspace, Slack, Travel, Banking), fino a 18 chiamate a
  tool per task.
- **ASB** (Zhang et al., 2025) e **AgentDyn** (costruito sopra il framework AgentDojo) —
  benchmark più recenti nella stessa famiglia.

Fonti: [AgentDyn](https://arxiv.org/html/2602.03117v1),
[Benchmarking Prompt-Injection Attacks on Tool-Integrated LLM Agents](https://openreview.net/forum?id=APaE1JUje1).

## Come usarli senza violare SPIRIT.md

`SPIRIT.md` principio 1 vieta specificamente il benchmark **del vendor sotto test**
(Gauntlet) — non un benchmark accademico indipendente come questi. Nessun conflitto di
principio nell'usarli come fonte, *a meno che* non emerga che il vendor si sia tarato
proprio su uno di questi (non verificato, da controllare solo se emergesse dubbio
concreto).

Non un'importazione diretta però, per due motivi reali:

1. **Principio 2** (metodologia dichiarata prima dei risultati): ogni nostro `TestCase`
   richiede `rationale`/`technique_target` **nostri**, con lo stesso criterio già usato
   per Gap 7 ("per effetto, non per intento") — non un'etichetta ereditata dalla
   tassonomia di qualcun altro senza passare dal nostro stesso ragionamento.
2. **Adattamento del contenuto** (vedi sotto) — non tutte le tecniche esterne hanno un
   analogo diretto nel nostro spazio d'azione.

**Uso consigliato**: fonte di ispirazione e cross-check per la copertura delle 14
tecniche dichiarate dal vendor, non un file da cui `load_dataset()` può leggere
direttamente.

## Chiarimento: lo schema è generico, il costo di adattamento è nel contenuto

Correzione a una sovrastima iniziale nella discussione (presentare "17+62 tool esterni
contro i nostri 6" come un vincolo strutturale — contestata correttamente dall'utente).
Verificato nel codice: `TestCase` (`src/toy_agent/schema.py:46-62`) non accoppia un caso
a nessun tool specifico — solo `label`/`technique_target`/`rationale`/`transcript`. Il
seed che innesca l'esecuzione è **una singola stringa di testo libero**
(`src/toy_agent/run_case.py:31-44`, `_extract_scenario()` — un turno utente, niente
altro), e l'agente sceglie da solo quali tool chiamare tra quelli che
`build_tool_registry()` gli mette a disposizione. Lo schema non sa e non gli importa
quanti tool esistono o cosa contengono.

Il vincolo reale non è nello schema — è che la **storia del prompt** deve potersi
risolvere con i tool che l'agente ha davvero. Per la maggioranza dei casi esterni è un
adattamento piccolo (riscrivere il testo, stessa tecnica su un tool nostro equivalente —
es. "posta su Slack" → "invia una mail"). Per una minoranza il vincolo è reale in un
altro senso: certe tecniche sfruttano affordance specifiche di tool che non hanno un
analogo diretto nel nostro set (es. un bug di visibilità condivisa in un tool
calendario) — lì serve reinventare il caso concettualmente o scartarlo per questo
dataset, non basta riscrivere il testo.

## Chiarimento: il set di 6 tool è estendibile, ma non a costo zero

Domanda: il limite di 6 tool ce lo siamo dato noi, non c'è niente che impedisca di
estenderlo? Confermato: nessun vincolo architetturale — `agent_loop.py`/`schema.py`/
`sequence.py` sono tutti generici, `build_tool_registry()` è solo una lista. Ma i 6
attuali non sono arbitrari:

- Mappano esplicitamente le 14 tecniche dichiarate dal vendor (tabella in
  `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md`, righe 20-26:
  `query_customer_db`→T0004/T0006/T0009, `send_email`→T0003/T0012, ecc.).
- Sono registrati in SourceLens (`aidr/data/source_registry.yaml` del vendor pinnato)
  come un unico server logico `toy_support` (risoluzione Gap 1/4/5, stesso design doc,
  sezione "Registro SourceLens per i tool del toy agent"), con **tre vincoli espliciti
  anti-distorsione**:
  1. codice statico, mai variato per caso di test;
  2. comportamento nascosto deciso in fase di design del tool, mai aggiustato dopo aver
     visto la reazione del detector;
  3. fonte unica di verità copiata nell'immagine al build (`COPY`, mai un mount runtime
     — deciso in Plan 3/Gap 8 per riproducibilità, principio 4 `SPIRIT.md`).

Estendere il set è legittimo ma ogni tool nuovo è una **decisione di design vera**: quale
tecnica target copre, codice reale scritto (mai finto "per il detector" — violerebbe il
vincolo 1 sopra), registrazione in SourceLens sotto lo stesso `toy_support`, rebuild
dell'immagine del container di controllo.

## Nessuna decisione presa

Solo terreno preparatorio. Quando si apre davvero Plan 5: partire da questo documento
invece di rifare la ricerca sui benchmark esterni da zero, e usare il chiarimento
schema-vs-contenuto per stimare quanto lavoro serve davvero per costruire il dataset —
probabilmente meno di quanto sembrasse all'inizio di questa discussione.
