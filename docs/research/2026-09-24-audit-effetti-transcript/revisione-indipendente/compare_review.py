"""Compare the independent reviewer's classificazione.csv with the mechanical rule.
Usage: python compare_review.py <path to classificazione.csv>"""
import csv, json, sys
from collections import Counter
from pathlib import Path
CSV_PATH = Path(sys.argv[1]).resolve()
HERE = Path(__file__).resolve().parent
REPO = Path(r"C:/Users/salva/Documents/github/agentic-security-audits")
sys.path.insert(0, str(REPO / "docs/research/2026-09-24-audit-effetti-transcript"))
import interpretation_key as ik  # noqa: E402
from toy_agent.serialization import transcript_from_dict  # noqa: E402
MAP = json.loads(Path(sys.argv[2]).resolve().read_text()) if len(sys.argv) > 2 else json.loads((HERE / "review_run_mapping.json").read_text())
NAMES = {"ATTACCO": "ATTACK", "NESSUN_ATTACCO": "NO_ATTACK", "NON_GIUDICABILE": "UNJUDGEABLE", "RICHIESTA": "REQUEST"}
rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
seen, agree, diff, conf = set(), 0, [], Counter()
for r in rows:
    run, cid = r["run"].strip(), r["case_id"].strip()
    seen.add((run, cid))
    f = REPO / "docs/reports" / MAP[run] / "raw" / f"{cid}.transcript.json"
    td = json.loads(f.read_text(encoding="utf-8"))
    rule = ik.reference(ik.cases[cid], transcript_from_dict(td), td)
    rev = NAMES.get(r["esito"].strip().upper(), r["esito"])
    conf[(rev == rule, r.get("confidenza", "").strip())] += 1
    if rev == rule: agree += 1
    else: diff.append(f"  {run} ({MAP[run][:22]}) {cid:52} rule={rule:11} reviewer={rev:11} [{r.get('confidenza','')}] {r.get('motivo','')[:140]}")
expected = {(k, p.name.removesuffix('.transcript.json')) for k, v in MAP.items() for p in (REPO / 'docs/reports' / v / 'raw').glob('*.transcript.json')}
print(f"rows {len(rows)}, expected {len(expected)}, missing {len(expected - seen)}, extra {len(seen - expected)}")
print(f"agree {agree}/{len(rows)}; by (agree, confidence): {dict(conf)}")
print("\n".join(diff))
