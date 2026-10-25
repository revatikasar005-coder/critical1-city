# Synthetic demo data: 100 zones (10x10 grid), no personal data anywhere.
import csv, os, random, datetime
random.seed(11)
os.makedirs("city_data", exist_ok=True)
Z = lambda r, c: "Z%02d" % (r * 10 + c + 1)
ALL = [Z(r, c) for r in range(10) for c in range(10)]
A = [Z(5,2), Z(5,3), Z(6,2), Z(6,3), Z(6,4)]      # power failure + far clinic
B = [Z(1,6), Z(1,7), Z(2,6), Z(2,7)]              # bus suspended + low income
C = [Z(8,7), Z(8,8), Z(9,7), Z(9,8), Z(9,9)]      # call drops + govt/crowd contradiction
D0 = datetime.date(2026, 9, 1)
day = lambda: str(D0 + datetime.timedelta(days=random.randint(0, 49)))
pz = lambda sp, p: random.choice(sp) if random.random() < p else random.choice(ALL)
def w(name, hdr, rows):
    with open("city_data/" + name, "w", newline="") as f:
        x = csv.writer(f); x.writerow(hdr); x.writerows(rows)

rows = []
for _ in range(399):
    z = pz(B, .3); rt = random.randint(1, 12)
    if z in B and random.random() < .6: ev, rt = "Bus route 4 suspended", 4
    else: ev = random.choices(["Normal service", "Route %d delayed" % rt, "Bus route %d suspended" % rt], [70, 22, 8])[0]
    rows.append([z, day(), rt, ev])
rows.append([Z(2,7), "2026-10-12", 12, "Road closed: construction"])   # zero-shot event
random.shuffle(rows); w("transit_logs.csv", ["zone","date","route","event"], rows)

rows = []
for _ in range(600):
    z = pz(A, .35); a = z in A
    rows.append([z, day(), round(random.uniform(14,40) if a else random.uniform(0,6), 1),
                 round(random.uniform(18,38) if a else random.uniform(45,65), 1)])
w("grid_sensors.csv", ["zone","date","voltage_drop_pct","water_pressure"], rows)

w("emergency_calls.csv", ["zone","date","anonymized_call_drops"],
  [[z, day(), random.randint(20,60) if z in C else random.randint(0,8)] for z in (pz(C, .35) for _ in range(500))])

w("economic_proxy.csv", ["zone","rent_index","vehicle_ownership_pct"],
  [[z, random.randint(10,30) if z in B else random.randint(45,90),
       random.randint(5,20) if z in B else random.randint(40,85)] for z in ALL])

noise = random.sample([z for z in ALL if z not in A], 5)
w("health_access.csv", ["zone","km_to_nearest_clinic"],
  [[z, round(random.uniform(2.5,4.5) if z in A else random.uniform(2.0,2.6) if z in noise else random.uniform(.3,1.8), 1)] for z in ALL])

rows = []
for _ in range(300):
    r = random.random(); s = random.choice(["govt", "crowd"])
    if r < .4: z = random.choice(C); cl = "power ok" if s == "govt" else "power cut"
    elif r < .55: z = random.choice(A); cl = "power cut"
    else: z = random.choice(ALL); cl = "power cut" if random.random() < .04 else "power ok"
    rows.append([z, day(), s, cl])
w("crowd_reports.csv", ["zone","date","source","claim"], rows)

w("ground_truth_zones.csv", ["zone","vulnerable"], [[z, 1 if z in A+B+C else 0] for z in ALL])
print("Cluster A:", A); print("Cluster B:", B, "(zero-shot construction event in", Z(2,7) + ")"); print("Cluster C:", C)
