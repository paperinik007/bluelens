import sys, json, glob, os
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.chdir(REPO)
sys.path.insert(0, str(REPO / 'src'))
from pathlib import Path
from toy_agent.dataset import load_dataset
from toy_agent.criteria import evaluate
from toy_agent.serialization import transcript_from_dict
cases = {c.case_id: c for c in load_dataset(Path('dataset'))}
runs = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob('docs/reports/*/verdicts.jsonl'))
for cid in sorted(cases):
    c = cases[cid]
    if c.label != 'malicious': continue
    print(f'\n### {cid} ({c.technique_target})  crit={json.dumps(c.attack_success_criteria.__class__.__name__)}')
    for r in runs:
        f = f'docs/reports/{r}/raw/{cid}.transcript.json'
        if not os.path.isfile(f): continue
        d = json.load(open(f, encoding='utf-8')); t = transcript_from_dict(d)
        ok = evaluate(c.attack_success_criteria, t)
        seq = []
        for x in d['turns']:
            tc = x.get('tool_call')
            if tc:
                a = json.dumps(tc['arguments'], ensure_ascii=False)[:60]
                seq.append(f"{tc['tool_name']}{a}{'✓' if tc['status']=='ok' else '✗'}")
        last = [x for x in d['turns'] if x['role']=='assistant' and x.get('content')]
        fin = (last[-1]['content'] if last else '')[:110].replace('\n',' ')
        print(f'  {r[:24]:24s} success={ok}')
        for s in seq: print('      ', s)
        print('       FINAL:', fin)
