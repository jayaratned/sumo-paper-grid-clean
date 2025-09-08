import sys
import csv
from pathlib import Path
import traci

# --------------------------------------------
# CLI: python safety_multi_seed.py [N_SEEDS] [SEED_START]
# Example: python safety_multi_seed.py 30 1
# Defaults: N_SEEDS=20, SEED_START=1
# --------------------------------------------
N_SEEDS    = int(sys.argv[1])
SEED_START = int(sys.argv[2])

SUMO_CONFIG = "safety.sumocfg"
SIM_END_S   = 3000.0
STEP_LEN_S  = 0.1

# Outputs
out_dir = Path("out_safety_runs")
out_dir.mkdir(parents=True, exist_ok=True)
detailed_csv = out_dir / "collisions_detailed.csv"
summary_csv  = out_dir / "collisions_summary.csv"

# CSV headers
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
        # Optional debug:
        # "--collision-output", str(out_dir / f"collisions_{seed}.xml")
    ]
    traci.start(sumo_cmd)

    detailed_rows = []
    involved_ids  = set()

    pre_speeds, pre_leaders = snapshot_prestate()

    while traci.simulation.getTime() <= SIM_END_S:
        traci.simulationStep()
        ego_brake()

        sim_t = traci.simulation.getTime()

        # Post-step speeds
        post_speeds = {}
        for vid in traci.vehicle.getIDList():
            try:
                post_speeds[vid] = traci.vehicle.getSpeed(vid)
            except traci.TraCIException:
                pass

        # --- Primary path: use getCollisions() and read collider/collidee if available
        collisions = traci.simulation.getCollisions()

        # We'll also use fallback if IDs are missing
        colliding_ids_fallback = []
        if not collisions:
            colliding_ids_fallback = traci.simulation.getCollidingVehiclesIDList()
        else:
            # Even if we have collisions, check if IDs exist; if not, use fallback too
            missing_all_ids = all(
                (getattr(c, "collider", None) is None and getattr(c, "collidee", None) is None)
                for c in collisions
            )
            if missing_all_ids:
                colliding_ids_fallback = traci.simulation.getCollidingVehiclesIDList()

        # --- Handle collisions with explicit pairs
        for c in collisions:
            collider = getattr(c, "collider", None)
            collidee = getattr(c, "collidee", None)
            lane     = getattr(c, "lane", "")
            pos_m    = getattr(c, "pos", float("nan"))
            ctype    = getattr(c, "type", "unknown")

            if collider is None and collidee is None:
                continue  # this pair gives us nothing; will be handled in fallback

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

        # --- Fallback path: no (or unusable) pairs; reconstruct via leader map
        if colliding_ids_fallback:
            # Unique set to avoid duplicate rows if multiple warnings
            ids = set(colliding_ids_fallback)

            # Try to form directed pairs (veh -> its pre-step leader if leader also collided)
            paired = set()
            for vid in list(ids):
                leader_info = pre_leaders.get(vid, None)
                if not leader_info:
                    continue
                leader_id, gap_m = leader_info
                if leader_id in ids and (vid, leader_id) not in paired:
                    # Treat vid as collider, leader as collidee
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

            # Any remaining unpaired vehicles: log single-vehicle collision rows
            # (keeps evidence that collision happened even if counterpart is unknown)
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
        # post -> pre for next step
        pre_speeds.update(post_speeds)
        for vid in traci.vehicle.getIDList():
            try:
                leader = traci.vehicle.getLeader(vid, 200.0)
                if leader is not None:
                    pre_leaders[vid] = leader
            except traci.TraCIException:
                pass

    traci.close(False)

    # Per-seed summary
    total_rows = len(detailed_rows)  # rows written for this seed
    unique_involved  = len(involved_ids)
    pileup_indicator = 1 if unique_involved >= 3 else 0

    return {
        "seed": seed,
        "total_collision_rows": total_rows,
        "unique_vehicles_involved": unique_involved,
        "pileup_indicator": pileup_indicator
    }, detailed_rows

# ---- Run seeds & write CSVs ----
for s in range(SEED_START, SEED_START + N_SEEDS):
    summary, rows = run_once(s)

    with open(detailed_csv, "a", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)

    with open(summary_csv, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            summary["seed"],
            summary["total_collision_rows"],
            summary["unique_vehicles_involved"],
            summary["pileup_indicator"]
        ])

print(f"Done. Detailed: {detailed_csv}  |  Summary: {summary_csv}")
