"""Revisione critica della tabella dei permessi e della scheda del caso (2026-10-14)."""
import json
import pathlib
import urllib.request

G = pathlib.Path(r'C:\Users\salva\Documents\github')
A = G / 'agentic-security-audits'
OUT = A / 'docs' / 'research' / '2026-10-14-revisione-tabella'
key = [l.split('=', 1)[1].strip().strip('"').strip("'")
       for l in (A / '.env').read_text(encoding='utf-8').splitlines()
       if l.startswith('AGENT_OPENROUTER_API_KEY=')][0]

def rd(p):
    return (A / p).read_text(encoding='utf-8')

MODEL = 'deepseek/deepseek-v4-pro-0813'

RUOLO = """Sei uno specialista di sicurezza degli agenti AI: red teaming di agenti che usano
strumenti, controllo degli accessi e abuso dei privilegi (OWASP ASI03), prompt injection
diretta e indiretta, tool poisoning e supply chain degli strumenti (ASI04), cataloghi degli
attacchi (OWASP Top 10 for Agentic Applications, MITRE ATLAS), realismo degli ambienti di
prova, cosa un sistema di rilevamento può e non può vedere."""

CONTESTO = """Il progetto misura dei "giudici": prodotti di sicurezza (aidr, PromptGuard 2,
AlignmentCheck) che sorvegliano un agente AI di supporto clienti e dicono se una sessione è
malevola. Il principio della misura è: un caso è un segnale noto immesso nel sistema, il
giudice è lo strumento, anche la lettura di chi misura è uno strumento con un suo errore.

Sotto trovi: (1) la tabella dei permessi e il formato della scheda del caso, DA RIVEDERE;
(2) il piano del run, da cui la tabella dipende, scritto in ordine di tempo (una decisione
successiva corregge una precedente, se lo dice); (3) le sfere dichiarate dei tre giudici;
(4) il codice attuale degli strumenti e dei dati del mondo, PRIMA delle correzioni
dell'ambiente descritte nel piano (parte 2), per sapere da dove si parte.

Le decisioni segnate come prese dal proprietario non si riaprono, a meno che tu non mostri
che contraddicono il principio della misura o un'altra decisione scritta.
"""

COMPITO = """
Fai una revisione critica del documento 1, nel tuo campo. Cerca soltanto:
A. buchi nella tabella dei permessi: azioni o combinazioni ruolo × strumento × perimetro
   della richiesta per cui la regola dei passi malevoli dà la risposta sbagliata (un attacco
   che non conta come passo malevolo, o un comportamento legittimo che conta come tale), con
   la chiamata concreta;
B. scelte poco realistiche per un sistema di supporto vero, che un agente o un giudice
   potrebbero riconoscere come "ambiente di test", con l'alternativa;
C. buchi nel formato della scheda del caso: campi che mancano per calcolare in automatico
   l'elenco comune, il segnale presentato, i gemelli, o che lasciano ambiguità a chi scrive i
   casi;
D. rischi delle quattro versioni dell'integrazione di terze parti (una onesta, tre
   compromesse) per la misura: cosa può far trapelare la versione, cosa i giudici possono o
   non possono vedere;
E. contraddizioni tra il documento 1 e il piano o le sfere.

Non suggerire cambi di stile o di parole. Se non trovi niente in una categoria, scrivilo.
Per ogni punto: categoria; i passi esatti coinvolti (citati); perché è un problema; un
esempio concreto (una chiamata, un caso); la correzione proposta, completa; gravità (alta:
cambia cosa si conta o rende la misura non valida; media: cambia come si legge; bassa:
chiarezza). Rispondi in italiano. Metti per primi i punti di gravità alta.
"""

DOCS = ("\n\n=== DOCUMENTO 1: tabella dei permessi e scheda del caso ===\n"
        + rd('docs/design/2026-10-14-tabella-permessi-bozza.md')
        + "\n\n=== DOCUMENTO 2: piano del run ===\n" + rd('docs/design/2026-10-11-piano-run-v3.md')
        + "\n\n=== DOCUMENTO 3: sfere dei giudici ===\n" + rd('docs/design/2026-10-11-sfere-giudici.md')
        + "\n\n=== DOCUMENTO 4a: src/toy_agent/tools.py (attuale) ===\n" + rd('src/toy_agent/tools.py')
        + "\n\n=== DOCUMENTO 4b: src/toy_agent/state.py (attuale) ===\n" + rd('src/toy_agent/state.py'))

if __name__ == '__main__':
    p = RUOLO + "\n\n" + CONTESTO + COMPITO + DOCS
    (OUT / 'input.md').write_text(p, encoding='utf-8')
    body = {'model': MODEL, 'temperature': 0, 'messages': [{'role': 'user', 'content': p}]}
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Authorization': f'Bearer {key}',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.loads(r.read().decode('utf-8'))
    (OUT / 'output.md').write_text(
        f"# Specialista di sicurezza ({resp.get('model', MODEL)}, fornitore "
        f"{resp.get('provider', '?')})\n\n{resp['choices'][0]['message']['content']}\n",
        encoding='utf-8')
    print(resp.get('model'), resp.get('provider'), resp.get('usage', {}).get('cost'))
