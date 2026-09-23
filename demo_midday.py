"""
demo_midday.py
===============

Demonstrates the "new agent joins mid-day" bonus feature end-to-end.

Scenario: a full day's packages get split into a MORNING batch and an
AFTERNOON batch. The morning batch is assigned and simulated with the
agents as given in the input file. Before the afternoon batch runs, a
brand-new agent joins (add_agent_mid_day) and each existing agent's
starting position for the afternoon is updated to wherever they ended up
after the morning (so the second half of the day continues realistically
from where the first half left off, rather than resetting everyone back
to their original start).

The afternoon batch is then assigned/simulated with the updated agent
roster (original agents + the new one), and the two halves are merged
into one combined end-of-day report.

Run:
    python3 demo_midday.py [input_file]

Defaults to test_cases/test_case_1.json if no file is given.
"""

import sys
import json

from delivery_system import (
    load_data,
    assign_packages,
    simulate_deliveries,
    generate_report,
    save_report,
    add_agent_mid_day,
)


def merge_reports(report_a, report_b):
    """Combine two per-agent reports (morning + afternoon) into one
    end-of-day report, recomputing efficiency and best_agent."""
    all_agents = set(report_a.keys()) | set(report_b.keys())
    all_agents.discard("best_agent")

    merged = {}
    best_agent = None
    best_efficiency = float("inf")

    for agent_id in sorted(all_agents):
        a = report_a.get(agent_id, {"packages_delivered": 0, "total_distance": 0.0})
        b = report_b.get(agent_id, {"packages_delivered": 0, "total_distance": 0.0})

        delivered = a["packages_delivered"] + b["packages_delivered"]
        distance = round(a["total_distance"] + b["total_distance"], 2)
        efficiency = round(distance / delivered, 2) if delivered > 0 else 0.0

        merged[agent_id] = {
            "packages_delivered": delivered,
            "total_distance": distance,
            "efficiency": efficiency,
        }

        if delivered > 0 and efficiency < best_efficiency:
            best_efficiency = efficiency
            best_agent = agent_id

    merged["best_agent"] = best_agent
    return merged


def run_demo(input_path):
    warehouses, agents, packages = load_data(input_path)

    midpoint = len(packages) // 2
    morning_packages = packages[:midpoint]
    afternoon_packages = packages[midpoint:]

    print(f"Loaded {len(packages)} packages, {len(agents)} agents, "
          f"{len(warehouses)} warehouses from {input_path}")
    print(f"Morning batch: {len(morning_packages)} packages "
          f"({[p['id'] for p in morning_packages]})")
    print(f"Afternoon batch: {len(afternoon_packages)} packages "
          f"({[p['id'] for p in afternoon_packages]})")
    print()

    # --- MORNING RUN: original agents only ---
    print("=" * 60)
    print("MORNING RUN (original agents)")
    print("=" * 60)
    morning_assignments = assign_packages(warehouses, agents, morning_packages)
    morning_sim = simulate_deliveries(agents, warehouses, morning_assignments)
    morning_report = generate_report(morning_sim)
    print(json.dumps(morning_report, indent=2))

    # Carry each agent forward to wherever they ended up after the morning,
    # so the afternoon continues realistically instead of resetting them.
    for agent_id, result in morning_sim.items():
        if result["packages_delivered"] > 0:
            agents[agent_id] = result["route"][-1][1]  # last position visited

    # --- NEW AGENT JOINS MID-DAY ---
    print()
    print("=" * 60)
    print("MID-DAY EVENT")
    print("=" * 60)
    # Placed near a cluster of warehouses still handling afternoon packages,
    # so the effect of the new agent is visible in the results below.
    new_agent_location = _pick_new_agent_location(warehouses, afternoon_packages)
    add_agent_mid_day(agents, "A_NEW", new_agent_location)

    # --- AFTERNOON RUN: original agents (at their new positions) + new agent ---
    print()
    print("=" * 60)
    print("AFTERNOON RUN (original agents at updated positions + new agent)")
    print("=" * 60)
    afternoon_assignments = assign_packages(warehouses, agents, afternoon_packages)
    afternoon_sim = simulate_deliveries(agents, warehouses, afternoon_assignments)
    afternoon_report = generate_report(afternoon_sim)
    print(json.dumps(afternoon_report, indent=2))

    # --- COMBINED END-OF-DAY REPORT ---
    print()
    print("=" * 60)
    print("COMBINED END-OF-DAY REPORT (morning + afternoon merged)")
    print("=" * 60)
    combined_report = merge_reports(morning_report, afternoon_report)
    print(json.dumps(combined_report, indent=2))

    save_report(morning_report, "midday_demo_morning_report.json")
    save_report(afternoon_report, "midday_demo_afternoon_report.json")
    save_report(combined_report, "midday_demo_combined_report.json")

    total_in = len(packages)
    total_out = sum(v["packages_delivered"] for k, v in combined_report.items() if k != "best_agent")
    print()
    print(f"Sanity check: packages in = {total_in}, packages delivered (combined) = {total_out}, "
          f"Check: {'OK' if total_in == total_out else 'MISMATCH'}")
    print(f"A_NEW (joined mid-day) delivered: "
          f"{combined_report.get('A_NEW', {}).get('packages_delivered', 0)} packages")


def _pick_new_agent_location(warehouses, afternoon_packages):
    """Place the new agent near the average location of the warehouses that
    afternoon packages ship from, so their impact on the results is visible."""
    used_warehouses = {p["warehouse"] for p in afternoon_packages}
    coords = [warehouses[w] for w in used_warehouses if w in warehouses]
    if not coords:
        return (0, 0)
    avg_x = sum(c[0] for c in coords) / len(coords)
    avg_y = sum(c[1] for c in coords) / len(coords)
    return (round(avg_x, 1), round(avg_y, 1))


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "test_cases/test_case_1.json"
    run_demo(path)
