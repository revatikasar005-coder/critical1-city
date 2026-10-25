# Explainable zone-risk engine. Zone-level only, no personal data. Synthetic demo data.
import csv, json, random, statistics as st
rd = lambda n: list(csv.DictReader(open("city_data/" + n)))
RAW = {n: rd(n + ".csv") for n in ["transit_logs","grid_sensors","emergency_calls","economic_proxy","health_access","crowd_reports"]}
TRUTH = {r["zone"] for r in rd("ground_truth_zones.csv") if r["vulnerable"] == "1"}
ZONES = ["Z%02d" % i for i in range(1, 101)]
W = {"grid": .7, "clinic": .5, "transit": .7, "econ": .5, "calls": .6, "crowd": .4}   # strength of each driver (noisy-OR)
LABEL = {"grid": "Power failure", "clinic": "Far from clinic", "transit": "Transit disruption", "econ": "Low income / no vehicle",
         "calls": "Emergency call drops", "crowd": "Crowd outage reports"}
ACT = {"grid": "Send mobile generators", "clinic": "Deploy medical team / mobile clinic", "transit": "Activate emergency bus route",
       "econ": "Arrange evacuation transport", "calls": "Boost local warning (SMS, loudspeaker)", "crowd": "Field-verify power status"}
PR = {"grid": (3, 2), "calls": (4, 2), "transit": (.08, 5)}   # shrink small samples toward normal (few records = less trust)
def stat(f, v):
    if f in PR: p, m = PR[f]; return (sum(v) + p * m) / (len(v) + m)
    return sum(v) if f == "crowd" else sum(v) / len(v)
NORM = {"grid": lambda v: v / 30, "clinic": lambda v: (v - 1) / 3, "transit": lambda v: (v - .1) / .5,
        "econ": lambda v: (v - 40) / 40, "calls": lambda v: (v - 5) / 25, "crowd": lambda v: v / 5}
def run(drop=0.0, seed=0):
    rnd = random.Random(seed)
    D = {n: [r for r in rows if rnd.random() >= drop] for n, rows in RAW.items()}
    raw = {f: {} for f in W}; recs = {z: 0 for z in ZONES}; contra = {z: 0 for z in ZONES}
    def add(f, z, v): raw[f].setdefault(z, []).append(v)
    for r in D["grid_sensors"]: add("grid", r["zone"], float(r["voltage_drop_pct"])); recs[r["zone"]] += 1
    for r in D["emergency_calls"]: add("calls", r["zone"], float(r["anonymized_call_drops"])); recs[r["zone"]] += 1
    for r in D["transit_logs"]:
        recs[r["zone"]] += 1
        add("transit", r["zone"], 1.0 if ("suspended" in r["event"] or "closed" in r["event"]) else 0.0)
    for r in D["economic_proxy"]: add("econ", r["zone"], 100 - (int(r["rent_index"]) + int(r["vehicle_ownership_pct"])) / 2)
    for r in D["health_access"]: add("clinic", r["zone"], float(r["km_to_nearest_clinic"]))
    cut = {z: 0 for z in ZONES}; ok = {z: 0 for z in ZONES}
    for r in D["crowd_reports"]:
        recs[r["zone"]] += 1
        if r["source"] == "crowd" and r["claim"] == "power cut": cut[r["zone"]] += 1
        if r["source"] == "govt" and r["claim"] == "power ok": ok[r["zone"]] += 1
    for z in ZONES: add("crowd", z, float(cut[z])); contra[z] = min(cut[z], ok[z])
    val = {f: {z: stat(f, v) for z, v in d.items()} for f, d in raw.items()}
    pct = {f: {z: max(0, min(1, NORM[f](v))) for z, v in d.items()} for f, d in val.items()}
    out = {}
    for z in ZONES:
        if recs[z] < 5: out[z] = None; continue                      # k=5 privacy suppression
        av = [f for f in W if z in pct[f]]; tw = sum(W[f] for f in av)
        pr = 1.0
        for f in av: pr *= 1 - W[f] * pct[f][z]
        out[z] = {"score": 1 - pr, "avail": tw,
                  "parts": {f: pct[f][z] for f in av}, "vals": {f: round(val[f][z], 2) for f in av}, "contra": contra[z]}
    thr = 0.5
    flagged = {z for z, o in out.items() if o and o["score"] >= thr}
    return out, flagged, thr, sum(1 for o in out.values() if o is None)
iou = lambda p: len(p & TRUTH) / max(len(p | TRUTH), 1)
out, fl, thr, sup = run()
seeds = [run(0.6, s) for s in range(30)]; ious = [iou(x[1]) for x in seeds]
nov = {}
for r in RAW["transit_logs"]: nov.setdefault(r["event"], []).append(r["zone"])
novel = {v[0]: k for k, v in nov.items() if len(v) == 1}
def clusters(S):
    S = set(S); res = []
    while S:
        q = [S.pop()]; c = set(q)
        while q:
            z = q.pop(); i = int(z[1:]) - 1; r, c0 = divmod(i, 10)
            for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr, nc = r + dr, c0 + dc
                if 0 <= nr < 10 and 0 <= nc < 10:
                    n = "Z%02d" % (nr * 10 + nc + 1)
                    if n in S: S.remove(n); c.add(n); q.append(n)
        res.append(sorted(c))
    return res
log = []
for z in sorted(fl):
    o = out[z]; drv = [f for f in sorted(o["parts"], key=lambda f: -o["parts"][f] * W[f]) if o["parts"][f] >= .5][:2]
    log.append({"zone": z, "risk": round(o["score"] * 100), "why": " + ".join("%s (%s)" % (LABEL[f], o["vals"][f]) for f in drv),
                "actions": [ACT[f] for f in drv] + (["Localized transit dispatch: new event '%s'" % novel[z]] if z in novel else []),
                "uncertain": o["contra"] >= 2})
with open("intervention_log.csv", "w", newline="") as f:
    x = csv.writer(f); x.writerow(["zone","risk_score","why","actions","govt_vs_crowd_conflict"])
    for l in log: x.writerow([l["zone"], l["risk"], l["why"], " | ".join(l["actions"]), l["uncertain"]])
with open("zone_scores.csv", "w", newline="") as f:
    x = csv.writer(f); x.writerow(["zone","risk_score","flagged"] + list(W))
    for z in ZONES: o = out[z]; x.writerow([z, round(o["score"]*100) if o else "suppressed", int(z in fl)] + ([round(o["parts"].get(k, 0), 2) for k in W] if o else []))
res = {"iou_full": round(iou(fl), 2), "iou_60pct_cut_mean": round(st.mean(ious), 2), "iou_60pct_cut_min": round(min(ious), 2),
       "flagged": sorted(fl), "clusters": clusters(fl), "zero_shot_zone_flagged": [z for z in novel if z in fl], "suppressed_full": sup,
       "suppressed_cut_mean": round(st.mean(s[3] for s in seeds), 1), "truth": sorted(TRUTH)}
json.dump(res, open("results.json", "w"), indent=1); print(json.dumps(res)); print(*[(l["zone"], l["risk"], l["why"]) for l in log], sep="\n")
