"""
FastBox Mystery Delivery System
================================

A logistics simulator for the fictional delivery company FastBox.

Given a set of warehouses, delivery agents, and packages, this program:
  1. Reads and parses the input JSON file manually (no pandas / external libs).
  2. Assigns each package to the nearest available agent, based on the
     Euclidean distance between the agent and the package's warehouse.
  3. Simulates one day of deliveries, tracking each agent's route and the
     total distance they travel.
  4. Produces a report (dict + report.json) showing packages delivered,
     total distance, and efficiency per agent, plus the overall best agent.

Bonus features (see the BONUS section near the bottom):
  - Random delivery delays
  - ASCII visualization of agent routes
  - Support for a new agent joining mid-day
  - CSV export of the top-performing agent

Author: (your name here)
"""

import json
import math
import random
import argparse
import csv
import sys


# ---------------------------------------------------------------------------
# 1. DATA LOADING / PARSING
# ---------------------------------------------------------------------------
#
# Two input shapes are supported, since real-world data doesn't always come
# in one tidy format:
#
#   Shape A (dict style)  -> "warehouses": {"W1": [x, y], ...}
#                             "agents":     {"A1": [x, y], ...}
#                             "packages":   [{"id": "P1", "warehouse": "W1",
#                                              "destination": [x, y]}, ...]
#
#   Shape B (list style)  -> "warehouses": [{"id": "W1", "location": [x, y]}, ...]
#                             "agents":     [{"id": "A1", "location": [x, y]}, ...]
#                             "packages":   [{"id": "P1", "warehouse_id": "W1",
#                                              "destination": [x, y]}, ...]
#
# load_data() normalizes both shapes into a single internal representation:
#   warehouses -> {id: (x, y)}
#   agents     -> {id: (x, y)}
#   packages   -> [{"id": str, "warehouse": str, "destination": (x, y)}, ...]


def load_data(filepath):
    """Read a JSON file from disk and normalize it into a common structure."""
    with open(filepath, "r") as f:
        raw = json.load(f)  # manual parsing of the JSON file

    warehouses = _normalize_locations(raw["warehouses"])
    agents = _normalize_locations(raw["agents"])
    packages = _normalize_packages(raw["packages"])

    return warehouses, agents, packages


def _normalize_locations(entries):
    """Turn either {"W1": [x, y]} or [{"id": "W1", "location": [x, y]}]
    into a plain dict: {"W1": (x, y)}."""
    result = {}
    if isinstance(entries, dict):
        # Shape A: already an id -> [x, y] mapping
        for entry_id, coords in entries.items():
            result[entry_id] = (coords[0], coords[1])
    else:
        # Shape B: a list of {"id": ..., "location": [x, y]}
        for entry in entries:
            result[entry["id"]] = (entry["location"][0], entry["location"][1])
    return result


def _normalize_packages(entries):
    """Normalize the packages list so every package dict has
    'id', 'warehouse', and 'destination' (as a tuple) keys."""
    packages = []
    for entry in entries:
        warehouse_id = entry.get("warehouse", entry.get("warehouse_id"))
        dest = entry["destination"]
        packages.append({
            "id": entry["id"],
            "warehouse": warehouse_id,
            "destination": (dest[0], dest[1]),
        })
    return packages


# ---------------------------------------------------------------------------
# 2. DISTANCE CALCULATION
# ---------------------------------------------------------------------------

def euclidean_distance(point_a, point_b):
    """Straight-line distance between two (x, y) points."""
    return math.sqrt((point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2)


# ---------------------------------------------------------------------------
# 3. AGENT-PACKAGE ASSIGNMENT
# ---------------------------------------------------------------------------

def assign_packages(warehouses, agents, packages):
    """
    Assign every package to the agent nearest to that package's warehouse
    (Euclidean distance from the agent's current location to the warehouse).

    Ties are broken by agent id (alphabetical), so results are deterministic.

    Returns: {agent_id: [package, package, ...]}  (insertion order preserved)
    """
    assignments = {agent_id: [] for agent_id in agents}

    for package in packages:
        warehouse_loc = warehouses.get(package["warehouse"])
        if warehouse_loc is None:
            # Package references a warehouse that doesn't exist - skip it,
            # but note it so nothing silently disappears.
            print(f"Warning: package {package['id']} references unknown "
                  f"warehouse '{package['warehouse']}' - skipped.")
            continue

        nearest_agent = None
        nearest_distance = math.inf
        for agent_id, agent_loc in sorted(agents.items()):
            dist = euclidean_distance(agent_loc, warehouse_loc)
            if dist < nearest_distance:
                nearest_distance = dist
                nearest_agent = agent_id

        if nearest_agent is not None:
            assignments[nearest_agent].append(package)

    return assignments


# ---------------------------------------------------------------------------
# 4. DELIVERY SIMULATION
# ---------------------------------------------------------------------------

def simulate_deliveries(agents, warehouses, assignments, simulate_delays=False,
                         delay_chance=0.3, max_delay_penalty=5.0, rng=None):
    """
    Simulate each agent's day: starting from their current location, an agent
    travels to the warehouse to pick up a package, then to the destination to
    deliver it, then on to the next warehouse for their next package, and so on.

    This models a realistic route (the agent's position updates after every
    leg) rather than assuming every trip starts back at the agent's home base.

    If simulate_delays=True (bonus), each delivery has a chance of a random
    delay, which is added to the agent's total distance as an equivalent
    "extra distance" penalty (representing rerouting / detours / waiting).

    Returns: {agent_id: {"packages_delivered": int,
                          "total_distance": float,
                          "route": [ (label, (x, y)), ... ],
                          "delays": [ (package_id, delay_amount), ... ]}}
    """
    if rng is None:
        rng = random.Random()

    results = {}
    for agent_id, package_list in assignments.items():
        current_position = agents[agent_id]
        total_distance = 0.0
        route = [("start", current_position)]
        delays = []

        for package in package_list:
            warehouse_loc = warehouses[package["warehouse"]]
            destination_loc = package["destination"]

            # Leg 1: current position -> warehouse (pickup)
            total_distance += euclidean_distance(current_position, warehouse_loc)
            current_position = warehouse_loc
            route.append((f"pickup {package['id']} @ {package['warehouse']}", current_position))

            # Leg 2: warehouse -> destination (drop-off)
            total_distance += euclidean_distance(current_position, destination_loc)
            current_position = destination_loc
            route.append((f"deliver {package['id']}", current_position))

            # --- BONUS: random delivery delay ---
            if simulate_delays and rng.random() < delay_chance:
                penalty = round(rng.uniform(0.5, max_delay_penalty), 2)
                total_distance += penalty
                delays.append((package["id"], penalty))

        results[agent_id] = {
            "packages_delivered": len(package_list),
            "total_distance": round(total_distance, 2),
            "route": route,
            "delays": delays,
        }

    return results


# ---------------------------------------------------------------------------
# 5. REPORT GENERATION
# ---------------------------------------------------------------------------

def generate_report(simulation_results):
    """
    Build the final report dict in the assignment's required shape:

    {
      "A1": {"packages_delivered": 2, "total_distance": 85.32, "efficiency": 42.66},
      ...
      "best_agent": "A1"
    }

    Efficiency = total_distance / packages_delivered (lower = more efficient,
    i.e. fewer distance-units spent per package). Agents with zero deliveries
    get an efficiency of 0.0 and are not eligible for "best_agent".
    """
    report = {}
    best_agent = None
    best_efficiency = math.inf

    for agent_id, result in simulation_results.items():
        delivered = result["packages_delivered"]
        distance = result["total_distance"]
        efficiency = round(distance / delivered, 2) if delivered > 0 else 0.0

        report[agent_id] = {
            "packages_delivered": delivered,
            "total_distance": distance,
            "efficiency": efficiency,
        }

        if delivered > 0 and efficiency < best_efficiency:
            best_efficiency = efficiency
            best_agent = agent_id

    report["best_agent"] = best_agent
    return report


def save_report(report, filepath="report.json"):
    """Write the report dict out to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {filepath}")


# ---------------------------------------------------------------------------
# BONUS FEATURES
# ---------------------------------------------------------------------------

def ascii_visualize_routes(agents, warehouses, packages, width=60, height=25):
    """
    Draw a simple ASCII-art map of warehouses (W), agents (A) and package
    destinations (.), scaled to fit a fixed-size grid. Purely for a quick
    visual sanity-check of the layout - not to scale precision.
    """
    all_points = list(agents.values()) + list(warehouses.values()) + \
        [p["destination"] for p in packages]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x_range = (max_x - min_x) or 1
    y_range = (max_y - min_y) or 1

    grid = [[" " for _ in range(width)] for _ in range(height)]

    def plot(point, symbol):
        gx = int((point[0] - min_x) / x_range * (width - 1))
        gy = int((point[1] - min_y) / y_range * (height - 1))
        grid[height - 1 - gy][gx] = symbol  # flip y so it reads bottom-up

    for pkg in packages:
        plot(pkg["destination"], ".")
    for w_loc in warehouses.values():
        plot(w_loc, "W")
    for a_loc in agents.values():
        plot(a_loc, "A")

    lines = ["".join(row) for row in grid]
    border = "+" + "-" * width + "+"
    print(border)
    for line in lines:
        print("|" + line + "|")
    print(border)
    print("Legend: W = warehouse, A = agent start position, . = package destination")


def add_agent_mid_day(agents, agent_id, location):
    """
    BONUS: handle a new agent joining mid-day. Simply registers the new
    agent at the given location so subsequent assignment/simulation runs
    can route packages to them. Any packages already assigned/simulated
    before this call are unaffected (agent joined "after" that batch).
    """
    if agent_id in agents:
        print(f"Warning: agent {agent_id} already exists - overwriting location.")
    agents[agent_id] = location
    print(f"Agent {agent_id} joined mid-day at {location}.")
    return agents


def export_top_performer_csv(report, filepath="top_performer.csv"):
    """BONUS: export the best agent's stats to a CSV file."""
    best_agent = report.get("best_agent")
    if best_agent is None:
        print("No best agent to export (no deliveries were made).")
        return

    stats = report[best_agent]
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency"])
        writer.writerow([best_agent, stats["packages_delivered"],
                          stats["total_distance"], stats["efficiency"]])
    print(f"Top performer ({best_agent}) exported to {filepath}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run(input_path, output_path="report.json", simulate_delays=False,
        visualize=False, export_csv=False, seed=None):
    warehouses, agents, packages = load_data(input_path)

    total_packages_in = len(packages)

    assignments = assign_packages(warehouses, agents, packages)

    rng = random.Random(seed) if seed is not None else random.Random()
    simulation_results = simulate_deliveries(
        agents, warehouses, assignments,
        simulate_delays=simulate_delays, rng=rng
    )

    report = generate_report(simulation_results)
    save_report(report, output_path)

    # Sanity check called out explicitly in the assignment notes:
    # "Make sure total packages delivered matches total packages."
    total_delivered = sum(r["packages_delivered"] for r in simulation_results.values())
    check = "OK" if total_delivered == total_packages_in else "MISMATCH"
    print(f"Packages in input: {total_packages_in} | Packages delivered: "
          f"{total_delivered} | Check: {check}")

    if simulate_delays:
        for agent_id, result in simulation_results.items():
            for pkg_id, penalty in result["delays"]:
                print(f"  Delay: agent {agent_id}, package {pkg_id}, +{penalty} units")

    if visualize:
        ascii_visualize_routes(agents, warehouses, packages)

    if export_csv:
        export_top_performer_csv(report)

    return report


def main():
    parser = argparse.ArgumentParser(description="FastBox Mystery Delivery System simulator")
    parser.add_argument("input", nargs="?", default="data.json",
                         help="Path to the input JSON file (default: data.json)")
    parser.add_argument("-o", "--output", default="report.json",
                         help="Path to write the report JSON (default: report.json)")
    parser.add_argument("--delays", action="store_true",
                         help="Bonus: simulate random delivery delays")
    parser.add_argument("--visualize", action="store_true",
                         help="Bonus: print an ASCII map of the routes")
    parser.add_argument("--csv", action="store_true",
                         help="Bonus: export the top performer to CSV")
    parser.add_argument("--seed", type=int, default=None,
                         help="Random seed, for reproducible delay simulation")
    args = parser.parse_args()

    run(args.input, args.output, simulate_delays=args.delays,
        visualize=args.visualize, export_csv=args.csv, seed=args.seed)


if __name__ == "__main__":
    main()
