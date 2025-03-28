import traci
import pandas as pd
from collections import defaultdict

# Simulation configuration
SUMO_CONFIG = "2lane.sumocfg"  # Replace with your SUMO config file
DETECTOR_POSITIONS = [f"{i}" for i in range(0, 6100, 100)]  # Correctly generates: 0, 100, 200, ..., 6000
TIME_INTERVAL = 300  # Data collection interval (5 minutes in seconds)
SIMULATION_DURATION = 3600  # Total simulation time (e.g., 1 hour)
DATA_COLLECTION_START = 650  # Time to start collecting data (e.g., 650 seconds)

MPS_TO_MPH = 2.23694  # Conversion factor: meters/second to miles/hour

def get_cross_section_ids(position):
    """Get the detector IDs for both lanes at a given position."""
    return [f"E1_0_{position}m", f"E1_1_{position}m"]

def main():
    # Start the SUMO simulation
    traci.start(["sumo", "-c", SUMO_CONFIG])

    # Initialize storage for aggregated data
    interval_data = defaultdict(lambda: defaultdict(list))
    results = defaultdict(list)

    step = 0
    collecting = False
    next_interval_start = DATA_COLLECTION_START  # Dynamic interval start time

    try:
        while step <= SIMULATION_DURATION:
            traci.simulationStep()

            # Start collecting data after the specified start time
            if step >= DATA_COLLECTION_START:
                collecting = True

            if collecting:
                for position in DETECTOR_POSITIONS:
                    # Get detector IDs for the current position
                    lane_detectors = get_cross_section_ids(position)

                    for detector_id in lane_detectors:
                        try:
                            flow = traci.inductionloop.getLastStepVehicleNumber(detector_id)  # Flow (vehicles)
                            speed = traci.inductionloop.getLastStepMeanSpeed(detector_id)  # Speed (m/s)
                        except traci.TraCIException:
                            print(f"Warning: Detector '{detector_id}' not found.")
                            continue

                        # Store data for aggregation
                        interval_data[position]["flow"].append(flow)
                        interval_data[position]["speed"].append(speed)

            # Aggregate and store data at the end of each interval
            if step == next_interval_start + TIME_INTERVAL:
                print(f"Aggregating data at simulation time: {step} seconds")

                for position, data in interval_data.items():
                    # Compute total flow (sum of all flows during interval)
                    total_flow = sum(data["flow"])  # Sum of flows over the interval

                    # Compute total speed, including stopped vehicles (speed = 0), ignoring no-vehicle cases (speed = -1)
                    total_speed = sum(speed for speed in data["speed"] if speed >= 0)
                    valid_speeds = sum(1 for speed in data["speed"] if speed >= 0)  # Count valid speeds

                    # Compute flow per hour per lane
                    avg_flow_per_hour = (total_flow / TIME_INTERVAL) * 3600 / 2  # veh/h/l (divide by 2 for 2 lanes)

                    # Compute average speed in mph
                    avg_speed_mph = (total_speed / valid_speeds) * MPS_TO_MPH if valid_speeds > 0 else 0

                    # Store results
                    results["time"].append(next_interval_start)  # Store the start of the interval
                    results["position"].append(position)
                    results["flow_veh_h_l"].append(round(avg_flow_per_hour, 2))
                    results["speed_mph"].append(round(avg_speed_mph, 2))

                    # Clear interval data for next collection
                    interval_data[position]["flow"].clear()
                    interval_data[position]["speed"].clear()

                # Update the next interval start
                next_interval_start += TIME_INTERVAL


            step += 1

    except KeyboardInterrupt:
        print("Simulation interrupted manually.")
    finally:
        traci.close()
        print("Simulation ended.")

        # Save results to CSV
        df = pd.DataFrame(results)
        df.to_csv("cross_section_data.csv", index=False)
        print("Data collection complete. Results saved to 'cross_section_data.csv'.")

if __name__ == "__main__":
    main()
