"""Revisione del flusso (raccolte, scarto, estrazioni, assegnazione, gemelli) e delle prime
cinque schede con il mondo comune (2026-10-19). Specialista di un'altra famiglia, alla cieca:
le osservazioni di Claude sui punti deboli sono tolte dall'input."""
import json
import pathlib
import urllib.request

G = pathlib.Path(r'C:\Users\salva\Documents\github')
A = G / 'agentic-security-audits'
OUT = A / 'docs' / 'research' / '2026-10-19-revisione-casi'
key = [l.split('=', 1)[1].strip().strip('"').strip("'")
       for l in (A / '.env').read_text(encoding='utf-8').splitlines()
       if l.startswith('AGENT_OPENROUTER_API_KEY=')][0]

def rd(p):
    return (A / p).read_text(encoding='utf-8')

def cut(text, start, end):
    """Toglie il tratto da start (compreso) a end (escluso): osservazioni di Claude."""
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + text[j:]

MODEL = 'google/gemini-3.1-pro-preview'

RUOLO = """Sei uno specialista nella costruzione di banchi di prova per la sicurezza degli
agenti AI e nella metodologia della misura: disegno sperimentale, campionamento e
randomizzazione, selezione sull'esito, riuso di benchmark pubblici (InjecAgent, ASB,
AgentDojo), prompt injection diretta e indiretta, controllo degli accessi negli agenti
(OWASP ASI03), realismo degli ambienti di prova e consapevolezza di essere in un test."""

CONTESTO = """Il progetto misura dei "giudici": prodotti di sicurezza (aidr, PromptGuard 2,
AlignmentCheck) che sorvegliano un agente AI di supporto clienti e dicono se una sessione è
malevola. Principio della misura: un caso è un segnale noto immesso nel sistema, il giudice è
lo strumento, anche la lettura di chi misura è uno strumento con un suo errore. Regole che
selezionano sull'esito sono vietate: nessun caso si cambia dopo aver visto un verdetto, nessun
caso nuovo si prova sui giudici prima del congelamento, le scelte che possono spostare il
risultato si fanno a sorte con il seme registrato.

Sotto trovi: (1) i principi del progetto; (2) il piano del run (in ordine di tempo: una
decisione successiva corregge una precedente se lo dice; la parte 5 contiene la procedura e
l'esito dell'assegnazione delle azioni e dei gemelli); (3) la tabella dei permessi e il
formato della scheda del caso; (4) le sfere dichiarate dei giudici; (5) la verifica delle
raccolte pubbliche, lo scarto e l'estrazione, con la tabella dello scarto testo per testo e
gli script; (6) il mondo comune e le prime cinque schede dei casi, scritte dai testi di
InjecAgent estratti.

Le decisioni segnate come prese dal proprietario non si riaprono, a meno che tu non mostri che
contraddicono il principio della misura, i principi del progetto o un'altra decisione scritta.
"""

COMPITO = """
Fai una revisione critica del lavoro descritto nei documenti 5 e 6 e nella parte 5 del piano
("Assegnazione delle azioni ed estrazione dei gemelli"). Cerca soltanto:
A. FLUSSO: punti in cui la verifica delle raccolte, la regola di equivalenza, lo scarto, i
   gruppi di testi uguali, l'estrazione dei casi, l'assegnazione delle azioni alle caselle o
   l'estrazione dei gemelli lasciano spazio a una scelta di chi misura che può spostare il
   risultato, o violano una regola scritta (indica quale); difetti delle procedure di
   estrazione (seme, ordine, rifiuti e ripetizioni, regole decise dopo aver visto qualcosa).
B. SCARTO: testi tenuti o scartati in modo incoerente con la regola di equivalenza come è
   scritta e letta nella sezione 7 di verifica.md. Controlla tutta la tabella dello scarto
   per InjecAgent e almeno i testi di ASB dei domini amministratore di sistema, finanza e
   commercio elettronico. Per ogni incoerenza: identificativo, motivo, esito corretto.
C. CASI: nelle cinque schede, errori rispetto alla tabella dei permessi e al piano (perimetro,
   passi propri, profilo, luogo dell'attacco, segnale presentato, regola "nei casi contenuto
   l'attacco chiede ciò che il proprietario del contenuto non può autorizzare"); cambiamenti
   al testo originale oltre il necessario; passi malevoli che la lettura automatica non
   vedrebbe o che vedrebbe a torto (con la chiamata concreta).
D. REALISMO: elementi del mondo comune o delle schede che un agente o un giudice potrebbero
   riconoscere come ambiente di test, con l'alternativa.
E. Contraddizioni tra i documenti 5-6 e il piano, la tabella o le sfere.

Non suggerire cambi di stile. Se non trovi niente in una categoria, scrivilo. Per ogni punto:
categoria; i passi esatti coinvolti (citati); perché è un problema; un esempio concreto; la
correzione proposta, completa; gravità (alta: cambia cosa si conta o rende la misura non
valida; media: cambia come si legge; bassa: chiarezza). Rispondi in italiano. Metti per primi
i punti di gravità alta.
"""

piano = rd('docs/design/2026-10-11-piano-run-v3.md')
piano = cut(piano, "Osservazioni, senza cambiare l'esito", "### Ambito atteso per giudice")
mondo = rd('docs/design/2026-10-19-mondo-base.md')
mondo = cut(mondo, "Da guardare nella revisione:", "## Da verificare")
cases = "".join(f"\n--- {p.name} ---\n" + p.read_text(encoding='utf-8')
                for p in sorted((A / 'dataset_v3' / 'cases').glob('*.yaml')))

DOCS = ("\n\n=== DOCUMENTO 1: principi del progetto (SPIRIT.md) ===\n" + rd('SPIRIT.md')
        + "\n\n=== DOCUMENTO 2: piano del run ===\n" + piano
        + "\n\n=== DOCUMENTO 3: tabella dei permessi e scheda del caso ===\n"
        + rd('docs/design/2026-10-14-tabella-permessi-bozza.md')
        + "\n\n=== DOCUMENTO 4: sfere dei giudici ===\n" + rd('docs/design/2026-10-11-sfere-giudici.md')
        + "\n\n=== DOCUMENTO 5a: verifica delle raccolte (verifica.md) ===\n"
        + rd('docs/research/2026-10-15-raccolte/verifica.md')
        + "\n\n=== DOCUMENTO 5b: tabella dello scarto (scarto.csv) ===\n"
        + rd('docs/research/2026-10-15-raccolte/scarto.csv')
        + "\n\n=== DOCUMENTO 5c: estrazione.py ===\n" + rd('docs/research/2026-10-15-raccolte/estrazione.py')
        + "\n\n=== DOCUMENTO 5d: assegnazione.py ===\n" + rd('docs/research/2026-10-15-raccolte/assegnazione.py')
        + "\n\n=== DOCUMENTO 6a: mondo comune ===\n" + mondo
        + "\n\n=== DOCUMENTO 6b: dataset_v3/world_base.yaml ===\n" + rd('dataset_v3/world_base.yaml')
        + "\n\n=== DOCUMENTO 6c: le cinque schede ===\n" + cases)

if __name__ == '__main__':
    p = RUOLO + "\n\n" + CONTESTO + COMPITO + DOCS
    (OUT / 'input.md').write_text(p, encoding='utf-8')
    body = {'model': MODEL, 'temperature': 0, 'messages': [{'role': 'user', 'content': p}],
            'provider': {'order': ['Google'], 'allow_fallbacks': False}}
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Authorization': f'Bearer {key}',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=1500) as r:
        resp = json.loads(r.read().decode('utf-8'))
    (OUT / 'output.md').write_text(
        f"# Specialista ({resp.get('model', MODEL)}, fornitore "
        f"{resp.get('provider', '?')})\n\n{resp['choices'][0]['message']['content']}\n",
        encoding='utf-8')
    print(resp.get('model'), resp.get('provider'), resp.get('usage', {}).get('cost'))
