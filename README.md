# FastBox Mystery Delivery System

A logistics simulator built for the "Mystery Delivery System" assignment.
Given warehouses, delivery agents, and packages, it assigns each package to
its nearest agent, simulates one day of deliveries, and produces a report of
packages delivered, distance traveled, and efficiency per agent.

## Files

- `delivery_system.py` — the full solution (single, well-commented script).
- `data.json` — the sample dataset from the assignment brief.
- `test_cases/` — the 10 provided test-case JSON files (all pass).
- `sample_output/` — an example `report.json` and `top_performer.csv`
  generated from `data.json`.

## How it works

1. **Parse input** (`load_data`) — reads the JSON manually with the built-in
   `json` module. Accepts either input shape: warehouses/agents as a plain
   `{"id": [x, y]}` dict (used by all 10 test cases) or as a list of
   `{"id": ..., "location": [x, y]}` objects (the shape shown in the PDF
   brief) — both are normalized to the same internal structure.
2. **Assign packages** (`assign_packages`) — for each package, computes the
   Euclidean distance from every agent to the package's warehouse and assigns
   the package to the closest agent (ties broken alphabetically by agent id).
3. **Simulate the day** (`simulate_deliveries`) — each agent's route is
   walked leg by leg: current position → warehouse (pickup) → destination
   (drop-off) → next warehouse → ... . Total distance accumulates realistically
   as the agent's position updates after every leg, rather than resetting to
   a home base each time.
4. **Report** (`generate_report`) — for each agent: packages delivered, total
   distance, and efficiency (`total_distance / packages_delivered`, i.e.
   average distance spent per package — lower is better). `best_agent` is
   whoever has the lowest efficiency among agents who delivered at least one
   package. Saved to `report.json` via `save_report`.

A built-in sanity check (from the assignment notes) confirms
`packages_delivered` (summed across agents) equals the number of packages in
the input.

## Usage

```bash
# Run on the default sample data.json, write report.json
python3 delivery_system.py

# Run on a specific input file, custom output path
python3 delivery_system.py test_cases/test_case_3.json -o report_3.json

# Turn on all bonus features
python3 delivery_system.py data.json --delays --visualize --csv --seed 42
```

CLI flags:
- `--delays` — bonus: randomly applies a delivery delay (added as extra
  distance) to some deliveries.
- `--visualize` — bonus: prints an ASCII map of warehouses (`W`), agent start
  positions (`A`), and package destinations (`.`).
- `--csv` — bonus: exports the best-performing agent's stats to
  `top_performer.csv`.
- `--seed N` — makes `--delays` reproducible.

## Bonus features implemented

- **Random delivery delays** — `simulate_deliveries(..., simulate_delays=True)`
  gives each delivery a chance of a random delay, added to the agent's total
  distance as an "extra distance" penalty (models detours/waiting).
- **ASCII route visualization** — `ascii_visualize_routes()` draws warehouses,
  agents, and destinations on a text grid.
- **New agent joining mid-day** — `add_agent_mid_day(agents, agent_id, location)`
  registers a new agent at a given location. See `demo_midday.py` for a full
  worked example (details below).
- **CSV export of top performer** — `export_top_performer_csv()` writes the
  best agent's stats to a CSV file.

### Mid-day agent joining — demo

`demo_midday.py` shows this feature running end-to-end, not just the function
existing:

```bash
python3 demo_midday.py test_cases/test_case_1.json
```

What it does:
1. Splits the input file's packages into a morning batch and an afternoon
   batch.
2. Runs assignment + simulation on the morning batch with the original agents.
3. Moves each agent that made a delivery to wherever their morning route left
   them off (so the afternoon starts from a realistic position, not a reset).
4. Calls `add_agent_mid_day()` to add a brand-new agent, placed near the
   warehouses the afternoon packages ship from.
5. Runs assignment + simulation on the afternoon batch with the updated
   roster (original agents at their new positions + the new agent).
6. Merges both halves into one combined end-of-day report and re-checks that
   total packages delivered still matches total packages in the input.

Sample output is saved in `sample_output/midday_demo/`:
`midday_demo_morning_report.json`, `midday_demo_afternoon_report.json`, and
`midday_demo_combined_report.json`. In the test_case_1.json run, the new
agent (`A_NEW`) picks up 3 of the 6 afternoon packages that would otherwise
have gone to the original agents — a visible, working demonstration of the
feature, and the 12/12 packages-delivered check still passes.

## Testing

The script was run against `data.json` and all 10 files in `test_cases/`;
every run reports `Check: OK`, confirming every package in the input is
accounted for in the output report.
