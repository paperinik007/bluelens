import sys, json, glob, os, collections
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.chdir(REPO)
sys.path.insert(0, str(REPO / 'src'))
from pathlib import Path
from toy_agent.dataset import load_dataset
from toy_agent.criteria import evaluate
from toy_agent.serialization import transcript_from_dict
cases = {c.case_id: c for c in load_dataset(Path('dataset'))}
k = json.load(open(glob.glob('docs/reports/*/raw/*.transcript.json')[0], encoding='utf-8'))
print('tool_call keys:', [t['tool_call'].keys() for t in k['turns'] if t.get('tool_call')][:1])
agg = collections.defaultdict(list)
for f in sorted(glob.glob('docs/reports/*/raw/*.transcript.json')):
    p = os.path.normpath(f).split(os.sep); run = p[-3][:24]; cid = p[-1].replace('.transcript.json', '')
    d = json.load(open(f, encoding='utf-8'))
    c = cases.get(cid)
    for x in d['turns']:
        tc = x.get('tool_call')
        if tc and tc['status'] != 'ok':
            msg = str(tc.get('result') or tc.get('error') or tc.get('output'))[:70]
            agg[(tc['tool_name'], msg)].append(f"{run}:{cid}[{c.label[0] if c else '?'}]")
for (tool, msg), where in sorted(agg.items()):
    print(f'\n{tool} | {msg} | n={len(where)}')
    for w in where: print('   ', w)
