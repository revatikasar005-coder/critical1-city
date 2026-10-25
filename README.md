# Critical1-City: Explainable Zone Risk Engine

Zone-level vulnerability detection during a city-wide crisis (power failure, transit disruption, etc.).
No personal data is used. All data is synthetic and for demo purposes.

## How to run

    python make_city_data.py   # generates synthetic data in city_data/
    python engine.py           # computes risk scores, writes outputs

Outputs: `zone_scores.csv`, `intervention_log.csv`, `results.json`

## How it works

- 100 zones (Z01-Z100) on a 10x10 grid.
- 6 drivers per zone: power failure, distance to clinic, transit disruption, low income / no vehicle, emergency call drops, crowd outage reports.
- Drivers are combined with a noisy-OR score (0-100). Zones scoring 50 or more are flagged.
- Every flagged zone gets the top 2 reasons plus a recommended action (e.g. send mobile generators, activate emergency bus route).

## Key features

- **Explainable:** each flag shows why it was flagged and what to do.
- **Privacy (k=5):** zones with fewer than 5 records are suppressed.
- **Robust to missing data:** small samples are shrunk toward normal, so few records mean less trust.
- **Conflicting sources:** if crowd reports and govt reports disagree, the zone is marked uncertain.
- **Zero-shot events:** a new, never-seen event (e.g. "Road closed: construction") triggers a localized dispatch action.

## Results (synthetic data)

| Metric | Value |
|---|---|
| IoU vs ground truth (full data) | 1.00 |
| IoU with 60% data removed (30 runs, mean) | 0.96 |
| IoU with 60% data removed (worst run) | 0.86 |
| Clusters found | 3 (A: 5 zones, B: 4 zones, C: 5 zones) |
| Zero-shot zones flagged | Z18, Z28, Z64 |

Note: the data is synthetic and generated from the ground truth, so these numbers show a working proof of concept, not real-world accuracy.
