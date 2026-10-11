"""Revisione indipendente del modello v3 intero, con tre revisori di famiglie diverse."""
import concurrent.futures as cf
import html
import json
import pathlib
import re
import urllib.request

G = pathlib.Path(r'C:\Users\salva\Documents\github')
A = G / 'agentic-security-audits'
OUT = A / 'docs' / 'research' / '2026-10-11-revisione-modello-v3'
OUT.mkdir(parents=True, exist_ok=True)
key = [l.split('=', 1)[1].strip().strip('"').strip("'")
       for l in (A / '.env').read_text(encoding='utf-8').splitlines()
       if l.startswith('AGENT_OPENROUTER_API_KEY=')][0]

rev = (A / 'docs/design/2026-10-09-revisione-modello.md').read_text(encoding='utf-8')
sfere = (A / 'docs/design/2026-10-11-sfere-giudici.md').read_text(encoding='utf-8')
page = (G / 'private-notes/bluelens/notes/2026-10-09-modello-v3-disegno.html').read_text(encoding='utf-8')
page = re.sub(r'<style.*?</style>', '', page, flags=re.S)
page = re.sub(r'<svg.*?</svg>', '[disegno della catena di misura]', page, flags=re.S)
page = html.unescape(re.sub(r'<[^>]+>', ' ', page))
page = re.sub(r'[ \t]+', ' ', page)
page = re.sub(r'\n\s*\n+', '\n', page)

PROMPT = """Sei un revisore indipendente di un modello di misura. Il progetto misura dei "giudici":
prodotti di sicurezza che sorvegliano un agente AI e dicono se una sessione è malevola. Il
principio della misura è: un caso è un segnale noto immesso nel sistema, il giudice è lo
strumento, anche la lettura di chi misura è uno strumento con un suo errore.

Sotto trovi tre documenti: (1) il file delle decisioni, scritto in ordine di tempo, dove una
decisione successiva può correggere una precedente (vale la più recente, se lo dice); (2) le
sfere dichiarate dei tre giudici; (3) il testo della pagina che riassume il modello.

Cerca soltanto:
A. contraddizioni: due decisioni in vigore, o due documenti, che dicono cose incompatibili;
B. decisioni che non seguono dai principi dichiarati nei documenti stessi;
C. buchi: situazioni concrete che le regole non coprono, cioè dove chi applica il modello non
   saprebbe cosa fare;
D. affermazioni presentate come fatti che i documenti non sostengono.

Non suggerire cambi di stile o di parole. Non riportare come problema una decisione che il file
stesso dichiara superata da una successiva. Se non trovi niente in una categoria, scrivilo.

Per ogni punto: categoria; i passi esatti coinvolti (citati); perché è un problema; un esempio
concreto (se possibile un caso del dataset nominato nei documenti); gravità (alta: cambia cosa
si conta; media: cambia come si legge; bassa: chiarezza). Rispondi in italiano. Metti per primi
i punti di gravità alta.

=== DOCUMENTO 1: file delle decisioni ===
""" + rev + "\n\n=== DOCUMENTO 2: sfere dei giudici ===\n" + sfere + \
    "\n\n=== DOCUMENTO 3: testo della pagina ===\n" + page

(OUT / 'input.md').write_text(PROMPT, encoding='utf-8')
MODELS = ['google/gemini-3.1-pro-preview', 'mistralai/mistral-large-4-0', 'deepseek/deepseek-v4-pro']


def call(model):
    body = {'model': model, 'temperature': 0, 'messages': [{'role': 'user', 'content': PROMPT}]}
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Authorization': f'Bearer {key}',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.loads(r.read().decode('utf-8'))
    name = model.split('/')[1]
    (OUT / f'output-{name}.md').write_text(
        f"# Revisore: {resp.get('model', model)}\n\n{resp['choices'][0]['message']['content']}\n",
        encoding='utf-8')
    return model, resp.get('usage', {}).get('cost'), resp.get('usage', {}).get('completion_tokens')


with cf.ThreadPoolExecutor(3) as ex:
    for res in ex.map(call, MODELS):
        print(res)
