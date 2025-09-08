# thesis-main.py
import sys
import csv
from pathlib import Path
import multiprocessing as mp
import time
import argparse
import random

# ---------- Worker: runs ONE seed ----------
def _worker_run_once(args):
    seed, SUMO_CONFIG, SIM_END_S, STEP_LEN_S = args
    import traci  # import inside process (Windows-safe)

    # ---- One-time attack state ----
    _action_done = False
    def _reset_attack_flag():
        nonlocal _action_done
        _action_done = False

    def ego_brake():
        """Trigger abrupt decel for 'ego' after 2250 m on E1, once per run."""
        nonlocal _action_done
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
        t_to_stop = max(v / 20.0, 0.1)     # ≈ 20 m/s², clamp small
        traci.vehicle.slowDown("ego", 0.0, t_to_stop)
        _action_done = True

    def snapshot_pre_speeds():
        speeds = {}
        for vid in traci.vehicle.getIDList():
            try:
                speeds[vid] = traci.vehicle.getSpeed(vid)
            except traci.TraCIException:
                pass
        return speeds

    def delta_v_kmh(pre_mps, post_mps):
        if pre_mps is None or post_mps is None:
            return None
        return abs(pre_mps - post_mps) * 3.6

    # ---- Start SUMO (do NOT change your sim params beyond collision flags) ----
    sumo_cmd = [
        "sumo",               # swap to "sumo-gui" if you want visuals
        "-c", SUMO_CONFIG,
        "--seed", str(seed),
        "--step-length", str(STEP_LEN_S),
        "--collision.action", "warn",
        "--collision.check-junctions", "true",
        "--collision.mingap-factor", "0",
        "--collision.stoptime", "600",
    ]
    traci.start(sumo_cmd)

    _reset_attack_flag()
    rows = []            # detailed per-collision rows (requested columns only)
    involved_ids = set() # for per-seed summary counts

    pre_speeds = snapshot_pre_speeds()

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

        # Primary collisions API
        collisions = traci.simulation.getCollisions()

        # Fallback if explicit IDs not exposed
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

        # Handle explicit pairs
        for c in collisions:
            collider = getattr(c, "collider", None)
            collidee = getattr(c, "collidee", None)
            lane     = getattr(c, "lane", "")
            pos_m    = getattr(c, "pos", float("nan"))
            ctype    = getattr(c, "type", "unknown")

            if collider is None and collidee is None:
                continue

            pre_col  = pre_speeds.get(collider, None) if collider else None
            post_col = post_speeds.get(collider, None) if collider else None
            dv1      = delta_v_kmh(pre_col, post_col)

            if collider: involved_ids.add(collider)
            if collidee: involved_ids.add(collidee)

            rows.append([
                seed, sim_t, lane, pos_m, ctype,
                collider, collidee,
                pre_col, post_col, dv1
            ])

        # Fallback: record vehicles with unknown partners
        if colliding_ids_fallback:
            for vid in set(colliding_ids_fallback):
                pre_v  = pre_speeds.get(vid, None)
                post_v = post_speeds.get(vid, None)
                dv     = delta_v_kmh(pre_v, post_v)
                rows.append([
                    seed, sim_t, "", float("nan"), "single_unknown_partner",
                    vid, "unknown",
                    pre_v, post_v, dv
                ])
                involved_ids.add(vid)

        pre_speeds = post_speeds

    traci.close(False)

    summary = {
        "seed": seed,
        "total_rows": len(rows),
        "unique_involved": len(involved_ids),
        "pileup_indicator": 1 if len(involved_ids) >= 3 else 0
    }
    return summary, rows

# ---------- Progress helpers ----------
def _fmt_eta(seconds: float) -> str:
    if seconds is None or seconds != seconds:
        return "?"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"

# ---------- Arg parsing & seed building ----------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("N_SEEDS", type=int, help="Number of sequential seeds (0=none)")
    p.add_argument("SEED_START", type=int, help="Start of sequential seeds (ignored if N_SEEDS=0)")
    p.add_argument("N_PROCS", nargs="?", type=int, default=1, help="Parallel processes (default=1)")

    # Flexible seed selection
    p.add_argument("--seeds", type=str, default="", help="Comma-separated explicit seeds")
    p.add_argument("--include", type=str, default="", help="Comma-separated seeds to force-include")
    p.add_argument("--rand", type=int, default=0, help="Number of random seeds to add")
    p.add_argument("--rand-min", type=int, default=1, help="Min random seed (inclusive)")
    p.add_argument("--rand-max", type=int, default=1_000_000, help="Max random seed (inclusive)")
    p.add_argument("--rand-seed", type=int, default=None, help="Python RNG seed for reproducible random generation")
    p.add_argument("--print-seeds", action="store_true", help="Print final seed list before running")
    return p.parse_args()

def build_seed_list(args):
    if args.rand_seed is not None:
        random.seed(args.rand_seed)

    seeds = []

    # 1) Sequential block
    if args.N_SEEDS > 0:
        seeds.extend(range(args.SEED_START, args.SEED_START + args.N_SEEDS))

    # 2) Explicit seeds
    if args.seeds.strip():
        seeds.extend(int(s.strip()) for s in args.seeds.split(",") if s.strip())

    # 3) Force-include list
    include_list = []
    if args.include.strip():
        include_list = [int(s.strip()) for s in args.include.split(",") if s.strip()]

    # 4) Random seeds (unique, not overlapping)
    existing = set(seeds) | set(include_list)
    need = args.rand
    while need > 0:
        r = random.randint(args.rand_min, args.rand_max)
        if r not in existing:
            seeds.append(r)
            existing.add(r)
            need -= 1

    # 5) Order: include first (in given order), then others without dupes
    seeds = [s for s in seeds if s not in set(include_list)]
    seeds = include_list + seeds
    return seeds

# ---------- Main ----------
def main():
    args = parse_args()

    SUMO_CONFIG = "safety.sumocfg"
    SIM_END_S   = 3000.0
    STEP_LEN_S  = 0.1

    seeds = build_seed_list(args)
    if not seeds:
        print("No seeds to run. Provide sequential N/START, --seeds, --include, or --rand.")
        sys.exit(1)

    if args.print_seeds:
        print("Seeds:", seeds)

    out_dir = Path("out_safety_runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    detailed_csv = out_dir / "collisions_detailed.csv"
    summary_csv  = out_dir / "collisions_summary.csv"

    detailed_header = [
        "seed","sim_time_s","lane","pos_m","collision_type",
        "collider","collidee",
        "pre_speed_collider_mps","post_speed_collider_mps","deltaV_collider_kmh"
    ]
    summary_header = ["seed","total_collision_rows","unique_vehicles_involved","pileup_indicator"]

    if not detailed_csv.exists():
        with open(detailed_csv, "w", newline="") as f:
            csv.writer(f).writerow(detailed_header)
    if not summary_csv.exists():
        with open(summary_csv, "w", newline="") as f:
            csv.writer(f).writerow(summary_header)

    work  = [(s, SUMO_CONFIG, SIM_END_S, STEP_LEN_S) for s in seeds]

    results = []
    total = len(work)
    start_t = time.perf_counter()

    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False

    if args.N_PROCS == 1:
        if use_tqdm:
            for item in tqdm(work, desc="Running seeds", unit="seed"):
                results.append(_worker_run_once(item))
        else:
            for idx, item in enumerate(work, 1):
                results.append(_worker_run_once(item))
                elapsed = time.perf_counter() - start_t
                rate = idx / max(elapsed, 1e-9)
                eta = (total - idx) / rate if rate > 0 else None
                print(f"\r[{idx}/{total}] elapsed {_fmt_eta(elapsed)} | ETA {_fmt_eta(eta)}",
                      end="", flush=True)
            print()
    else:
        if use_tqdm:
            with mp.get_context("spawn").Pool(processes=args.N_PROCS) as pool:
                for res in tqdm(pool.imap_unordered(_worker_run_once, work),
                                total=total, desc=f"Running seeds x{args.N_PROCS}", unit="seed"):
                    results.append(res)
        else:
            with mp.get_context("spawn").Pool(processes=args.N_PROCS) as pool:
                for idx, res in enumerate(pool.imap_unordered(_worker_run_once, work), 1):
                    results.append(res)
                    elapsed = time.perf_counter() - start_t
                    rate = idx / max(elapsed, 1e-9)
                    eta = (total - idx) / rate if rate > 0 else None
                    print(f"\r[{idx}/{total}] elapsed {_fmt_eta(elapsed)} | ETA {_fmt_eta(eta)}",
                          end="", flush=True)
            print()

    with open(detailed_csv, "a", newline="") as fdet, open(summary_csv, "a", newline="") as fsum:
        wdet = csv.writer(fdet)
        wsum = csv.writer(fsum)
        for summary, rows in results:
            wdet.writerows(rows)
            wsum.writerow([
                summary["seed"],
                summary["total_rows"],
                summary["unique_involved"],
                summary["pileup_indicator"]
            ])

    print(f"Done. Detailed: {detailed_csv}  |  Summary: {summary_csv}")

if __name__ == "__main__":
    main()
