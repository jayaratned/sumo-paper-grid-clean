#!/usr/bin/env python3
import sys
import csv
import time
from statistics import median
from pathlib import Path
import platform
import os

import traci

# Optional: peak RAM (Python + SUMO child)
try:
    import psutil
except Exception:
    psutil = None

# --------------------------------------------
# CLI (optional):
#   python safety_multi_seed.py [N_SEEDS] [SEED_START]
# Defaults: N_SEEDS=10, SEED_START=1
# --------------------------------------------
def parse_cli():
    if len(sys.argv) >= 2:
        try:
            n = int(sys.argv[1])
        except ValueError:
            n = 10
    else:
        n = 10
    if len(sys.argv) >= 3:
        try:
            s0 = int(sys.argv[2])
        except ValueError:
            s0 = 1
    else:
        s0 = 1
    return n, s0

N_SEEDS, SEED_START = parse_cli()

SUMO_CONFIG = "safety.sumocfg"
SIM_END_S   = 3600.0
STEP_LEN_S  = 0.1

# Outputs
out_dir = Path("out_safety_runs")
out_dir.mkdir(parents=True, exist_ok=True)
detailed_csv = out_dir / "collisions_detailed.csv"
summary_csv  = out_dir / "collisions_summary.csv"
runtime_csv  = out_dir / "runtime_summary.csv"

# Write headers if files don't exist
if not detailed_csv.exists():
    with open(detailed_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "seed","sim_time_s","lane","pos_m","collision_type",
            "collider","collidee",
            "pre_speed_collider_mps","post_speed_collider_mps","deltaV_collider_kmh",
            "pre_speed_collidee_mps","post_speed_collidee_mps","deltaV_collidee_kmh",
            "pre_gap_m","closing_speed_kmh","ttc_s"
        ])

if not summary_csv.exists():
    with open(summary_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed","total_collision_rows","unique_vehicles_involved","pileup_indicator"])

if not runtime_csv.exists():
    with open(runtime_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "seed", "sim_seconds", "wall_clock_s", "sim_speed_x",
            "peak_ram_gb_total", "peak_ram_gb_sumo_only",
            "vehicles_total", "steps", "sumo_version"
        ])

# ---- Attack logic (single: emergency brake) ----
_action_done = False
def _reset_attack_flag():
    global _action_done
    _action_done = False

def ego_brake():
    """Trigger abrupt decel for 'ego' after 2250 m on E1, once per run."""
    global _action_done
    if _action_done:
        return
    if "ego" not in traci.vehicle.getIDList():
        return
    if traci.vehicle.getRoadID("ego") != "E1":
        return
    if traci.vehicle.getLanePosition("ego") <= 2250:
        return
    traci.vehicle.setSpeedMode("ego", 0)
    traci.vehicle.setLaneChangeMode("ego", 0)
    v = traci.vehicle.getSpeed("ego")  # m/s
    t_to_stop = max(v / 20.0, 0.1)     # ≈ 20 m/s^2, clamp small
    traci.vehicle.slowDown("ego", 0.0, t_to_stop)
    _action_done = True

# ---- Helpers ----
def snapshot_prestate():
    """Return dicts: pre-step speeds, and pre-step leaders (id,gap) up to 200 m."""
    speeds, leaders = {}, {}
    for vid in traci.vehicle.getIDList():
        try:
            speeds[vid] = traci.vehicle.getSpeed(vid)
            leader = traci.vehicle.getLeader(vid, 200.0)  # (leaderID, gap_m) or None
            if leader is not None:
                leaders[vid] = leader
        except traci.TraCIException:
            pass
    return speeds, leaders

def delta_v_kmh(pre_mps, post_mps):
    if pre_mps is None or post_mps is None:
        return None
    return abs(pre_mps - post_mps) * 3.6

def closing_speed_and_ttc(pre_speed_coll_mps, pre_speed_col2_mps, pre_gap_m):
    if pre_gap_m is None or pre_speed_coll_mps is None or pre_speed_col2_mps is None:
        return (None, None)
    rel = pre_speed_coll_mps - pre_speed_col2_mps  # m/s
    if rel <= 0:
        return (0.0, None)
    return (rel * 3.6, pre_gap_m / max(rel, 1e-6))

def get_peak_ram_gb_trackers():
    """Return two callables that you can call to update peak totals:
       - update_total() -> updates & returns peak GB for Python + all children
       - update_sumo()  -> updates & returns peak GB for SUMO child(ren) only
    """
    if psutil is None:
        return (lambda: None, lambda: None)

    this = psutil.Process(os.getpid())
    peak_total = [0.0]
    peak_sumo  = [0.0]

    def update_total():
        total = 0
        try:
            total += this.memory_info().rss
        except psutil.Error:
            pass
        for ch in this.children(recursive=True):
            try:
                total += ch.memory_info().rss
            except psutil.Error:
                pass
        gb = total / 1e9
        if gb > peak_total[0]:
            peak_total[0] = gb
        return peak_total[0]

    def update_sumo():
        total = 0
        for ch in this.children(recursive=True):
            try:
                name = (ch.name() or "").lower()
                cmd  = " ".join(ch.cmdline()).lower() if ch.cmdline() else ""
                if "sumo" in name or "sumo" in cmd:
                    total += ch.memory_info().rss
            except psutil.Error:
                pass
        gb = total / 1e9
        if gb > peak_sumo[0]:
            peak_sumo[0] = gb
        return peak_sumo[0]

    return update_total, update_sumo

# ---- One seeded run ----
def run_once(seed: int):
    _reset_attack_flag()

    sumo_cmd = [
        "sumo",                 # swap to "sumo-gui" to view
        "-c", SUMO_CONFIG,
        "--seed", str(seed),
        "--step-length", str(STEP_LEN_S),
        "--collision.action", "warn",
        "--collision.check-junctions", "true",
        "--collision.mingap-factor", "0",
        "--collision.stoptime", "3"
        # "--collision-output", str(out_dir / f"collisions_{seed}.xml")
    ]

    # Per-seed timers & trackers
    seed_wall_start = time.perf_counter()
    steps = 0
    vehicles_seen = set()

    # Peak RAM trackers
    update_peak_total, update_peak_sumo = get_peak_ram_gb_trackers()
    peak_total_gb = None
    peak_sumo_gb  = None

    # Start SUMO
    traci.start(sumo_cmd)
    try:
        # version string e.g., "SUMO 1.18.0 ..."
        ver_tuple = traci.getVersion()  # (int, int, 'string')
        sumo_version = ver_tuple[2] if len(ver_tuple) >= 3 else str(ver_tuple)

        detailed_rows = []
        involved_ids  = set()

        pre_speeds, pre_leaders = snapshot_prestate()

        # memory sample throttle: check every ~0.25s simulated
        mem_sample_every = max(1, int(0.25 / STEP_LEN_S))
        while traci.simulation.getTime() <= SIM_END_S:
            traci.simulationStep()
            steps += 1
            ego_brake()

            # Track vehicles observed
            try:
                vehicles_seen.update(traci.vehicle.getIDList())
            except traci.TraCIException:
                pass

            # Peak RAM sampling
            if psutil and steps % mem_sample_every == 0:
                peak_total_gb = update_peak_total()
                peak_sumo_gb  = update_peak_sumo()

            sim_t = traci.simulation.getTime()

            # Post-step speeds
            post_speeds = {}
            for vid in traci.vehicle.getIDList():
                try:
                    post_speeds[vid] = traci.vehicle.getSpeed(vid)
                except traci.TraCIException:
                    pass

            # --- Primary path: collisions with explicit pairs
            collisions = traci.simulation.getCollisions()
            colliding_ids_fallback = []
            if not collisions:
                colliding_ids_fallback = traci.simulation.getCollidingVehiclesIDList()
            else:
                missing_all_ids = all(
                    (getattr(c, "collider", None) is None and getattr(c, "collidee", None) is None)
                    for c in collisions
                )
                if missing_all_ids:
                    colliding_ids_fallback = traci.simulation.getCollidingVehiclesIDList()

            for c in collisions:
                collider = getattr(c, "collider", None)
                collidee = getattr(c, "collidee", None)
                lane     = getattr(c, "lane", "")
                pos_m    = getattr(c, "pos", float("nan"))
                ctype    = getattr(c, "type", "unknown")

                if collider is None and collidee is None:
                    continue

                pre_col   = pre_speeds.get(collider, None) if collider else None
                post_col  = post_speeds.get(collider, None) if collider else None
                pre_col2  = pre_speeds.get(collidee, None) if collidee else None
                post_col2 = post_speeds.get(collidee, None) if collidee else None

                dv1 = delta_v_kmh(pre_col,  post_col)
                dv2 = delta_v_kmh(pre_col2, post_col2)

                pre_gap_m = None
                closing_kmh = None
                ttc_s = None
                if collider and collider in pre_leaders:
                    leader_id, gap_m = pre_leaders[collider]
                    if collidee and leader_id == collidee:
                        pre_gap_m = gap_m
                        closing_kmh, ttc_s = closing_speed_and_ttc(pre_col, pre_col2, pre_gap_m)

                if collider: involved_ids.add(collider)
                if collidee: involved_ids.add(collidee)

                detailed_rows.append([
                    seed, sim_t, lane, pos_m, ctype,
                    collider, collidee,
                    pre_col, post_col, dv1,
                    pre_col2, post_col2, dv2,
                    pre_gap_m, closing_kmh, ttc_s
                ])

            # --- Fallback reconstruction
            if colliding_ids_fallback:
                ids = set(colliding_ids_fallback)
                paired = set()
                for vid in list(ids):
                    leader_info = pre_leaders.get(vid, None)
                    if not leader_info:
                        continue
                    leader_id, gap_m = leader_info
                    if leader_id in ids and (vid, leader_id) not in paired:
                        pre_col   = pre_speeds.get(vid, None)
                        post_col  = post_speeds.get(vid, None)
                        pre_col2  = pre_speeds.get(leader_id, None)
                        post_col2 = post_speeds.get(leader_id, None)
                        dv1 = delta_v_kmh(pre_col,  post_col)
                        dv2 = delta_v_kmh(pre_col2, post_col2)
                        closing_kmh, ttc_s = closing_speed_and_ttc(pre_col, pre_col2, gap_m)
                        detailed_rows.append([
                            seed, sim_t, "", float("nan"), "reconstructed",
                            vid, leader_id,
                            pre_col, post_col, dv1,
                            pre_col2, post_col2, dv2,
                            gap_m, closing_kmh, ttc_s
                        ])
                        involved_ids.update([vid, leader_id])
                        paired.add((vid, leader_id))
                # Singles
                for vid in ids:
                    if any(vid in pair for pair in paired):
                        continue
                    pre_v  = pre_speeds.get(vid, None)
                    post_v = post_speeds.get(vid, None)
                    dv     = delta_v_kmh(pre_v, post_v)
                    detailed_rows.append([
                        seed, sim_t, "", float("nan"), "single_unknown_partner",
                        vid, "unknown",
                        pre_v, post_v, dv,
                        None, None, None,
                        None, None, None
                    ])
                    involved_ids.add(vid)

            # Roll snapshots
            pre_speeds, pre_leaders = {}, {}
            pre_speeds.update(post_speeds)
            for vid in traci.vehicle.getIDList():
                try:
                    leader = traci.vehicle.getLeader(vid, 200.0)
                    if leader is not None:
                        pre_leaders[vid] = leader
                except traci.TraCIException:
                    pass

        # End loop
    finally:
        # Cleanly close SUMO even on exceptions
        try:
            traci.close(False)
        except Exception:
            pass

    # Per-seed summary
    total_rows = len(detailed_rows)
    unique_involved  = len(involved_ids)
    pileup_indicator = 1 if unique_involved >= 3 else 0

    # Persist collision logs
    with open(detailed_csv, "a", newline="") as f:
        w = csv.writer(f)
        w.writerows(detailed_rows)
    with open(summary_csv, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([seed, total_rows, unique_involved, pileup_indicator])

    # Wall-clock + sim speed
    wall_clock_s = time.perf_counter() - seed_wall_start
    sim_seconds  = SIM_END_S
    sim_speed_x  = sim_seconds / wall_clock_s if wall_clock_s > 0 else None

    # Vehicles total observed
    vehicles_total = len(vehicles_seen)

    # Peak RAMs (may be None if psutil missing)
    peak_total_gb = peak_total_gb if peak_total_gb is not None else ""
    peak_sumo_gb  = peak_sumo_gb  if peak_sumo_gb  is not None else ""

    # Write runtime line
    with open(runtime_csv, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            seed, sim_seconds, f"{wall_clock_s:.3f}",
            f"{sim_speed_x:.3f}" if sim_speed_x else "",
            f"{peak_total_gb:.3f}" if peak_total_gb != "" else "",
            f"{peak_sumo_gb:.3f}"  if peak_sumo_gb  != "" else "",
            vehicles_total, steps, str(sumo_version)
        ])

    return {
        "seed": seed,
        "wall_clock_s": wall_clock_s,
        "sim_speed_x": sim_speed_x,
        "peak_total_gb": peak_total_gb,
        "peak_sumo_gb": peak_sumo_gb,
        "vehicles_total": vehicles_total
    }

# ---- Run seeds & print aggregate ----
def main():
    print(f"Running {N_SEEDS} seeds sequentially, starting at {SEED_START}")
    print(f"Host: {platform.platform()} | Python: {platform.python_version()} | psutil: {'yes' if psutil else 'no'}")
    results = []
    for s in range(SEED_START, SEED_START + N_SEEDS):
        print(f"  → Seed {s} ...", end="", flush=True)
        r = run_once(s)
        results.append(r)
        print(f" done. wall={r['wall_clock_s']:.2f}s, speed={r['sim_speed_x']:.2f}×, "
              f"peakRAM(total)={r['peak_total_gb'] or 'NA'} GB")
    # Aggregate (median & IQR)
    try:
        ws = [r["wall_clock_s"] for r in results]
        sx = [r["sim_speed_x"] for r in results if r["sim_speed_x"]]
        med_w = median(ws)
        q1_w  = sorted(ws)[len(ws)//4]
        q3_w  = sorted(ws)[(3*len(ws))//4]
        med_s = median(sx) if sx else None
        q1_s  = sorted(sx)[len(sx)//4] if sx else None
        q3_s  = sorted(sx)[(3*len(sx))//4] if sx else None
        print("\nAggregate (per-seed, sequential):")
        print(f"  Wall-clock (s): median {med_w:.2f}  [IQR {q1_w:.2f}–{q3_w:.2f}]")
        if med_s:
            print(f"  Sim speed (×): median {med_s:.2f}  [IQR {q1_s:.2f}–{q3_s:.2f}]")
    except Exception:
        pass
    print(f"\nDone. Detailed: {detailed_csv} | Summary: {summary_csv} | Runtime: {runtime_csv}")

if __name__ == "__main__":
    main()
