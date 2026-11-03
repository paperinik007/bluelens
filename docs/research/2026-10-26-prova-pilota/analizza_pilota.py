"""Riassunto compatto dei verdetti della prova pilota per un giudice: instabilità tra i verdetti ripetuti, effetto della
lingua, quota di allarmi per gruppo. Uso: python analizza_pilota.py alignmentcheck|aidr|promptguard"""
import csv, glob, json, sys, collections, statistics
J = sys.argv[1]
grp = {r["id"]: (r["gruppo"], r["caso"], r["prova_lingua"]) for r in csv.DictReader(open("estrazione.csv", encoding="utf-8"))}
def load(d):
    out = collections.defaultdict(dict)
    for f in glob.glob(f"{d}/*_{J}_[0-9].json"):
        x = json.load(open(f, encoding="utf-8")); out[x["session_id"]][x["repeat"]] = x
    return out
en, it = load("verdetti-en"), load("verdetti-it")
ok = lambda x: x["verdict"]["status"] == "ok"
lab = lambda x: x["verdict"]["label"]
print(f"{J}: verdetti en {sum(len(v) for v in en.values())}, it {sum(len(v) for v in it.values())}; errori nel verdetto {sum(1 for v in list(en.values())+list(it.values()) for x in v.values() if not ok(x))}")
mixed = []; full = 0; allm = collections.Counter()
for sid, v in sorted(en.items()):
    labels = [lab(x) for x in v.values() if ok(x)]
    if len(labels) < 5: continue
    full += 1
    if len(set(labels)) > 1: mixed.append((sid, grp[sid][0], grp[sid][1][:32], labels.count("malicious"), len(labels)))
    allm[(grp[sid][0], labels.count("malicious") > 0)] += 1
print(f"sessioni con 5 verdetti validi: {full}; con etichette diverse tra i 5: {len(mixed)}")
for m in mixed: print("  instabile:", m)
for g in ("risultato malevolo", "benigna", "rifiuto"):
    n = sum(1 for s in en if grp[s][0] == g and len([1 for x in en[s].values() if ok(x)]) >= 5)
    print(f"  {g:19s} sessioni con almeno un allarme su 5: {allm[(g, True)]}/{n}")
diff = []; tested = 0
for sid, v in it.items():
    e = [lab(en[sid][r]) for r in (1, 2, 3) if r in en[sid] and ok(en[sid][r])]; i = [lab(x) for x in v.values() if ok(x)]
    if len(e) == 3 and len(i) == 3:
        tested += 1
        if e.count("malicious") != i.count("malicious"): diff.append((sid, grp[sid][1][:30], f"en {e.count('malicious')}/3", f"it {i.count('malicious')}/3"))
print(f"lingua: {tested} sessioni confrontabili (3 en contro 3 it); con numero di allarmi diverso: {len(diff)}")
for d in diff: print("  ", d)
costs = [x["cost_usd"] for v in list(en.values()) + list(it.values()) for x in v.values()]
print(f"costo medio a verdetto {statistics.mean(costs):.5f}, totale {sum(costs):.4f}")
