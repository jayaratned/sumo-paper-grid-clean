import traci
import pandas as pd
from collections import defaultdict

# Simulation configuration
SUMO_CONFIG = "2lane.sumocfg"  # Replace with your SUMO config file
DETECTOR_POSITIONS = [f"{i}" for i in range(0, 6100, 100)]  # Correctly generates: 0, 100, 200, ..., 6000
TIME_INTERVAL = 900  # Data collection interval (5 minutes in seconds)
SIMULATION_DURATION = 3900  # Total simulation time (e.g., 1 hour)
DATA_COLLECTION_START = None  # Dynamically set when 'ego' vehicle stops

MPS_TO_MPH = 2.23694  # Conversion factor: meters/second to miles/hour
action = False  # Flag for ego braking

def get_cross_section_ids(position):
    """Get the detector IDs for both lanes at a given position."""
    return [f"E1_0_{position}m", f"E1_1_{position}m"]

def ego_brake(step):
    """Handles the braking logic for the ego vehicle."""
    global action, DATA_COLLECTION_START

    # Check if 'ego' vehicle is in the simulation
    if 'ego' in traci.vehicle.getIDList():
        if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 5000 and not action:
            # Disable safety checks for the 'attack'
            traci.vehicle.setSpeedMode('ego', 0)
            traci.vehicle.setLaneChangeMode('ego', 0)

            # Calculate time to stop
            time_to_stop = traci.vehicle.getSpeed('ego') / 9  # Assume deceleration rate of 9 m/s^2
            traci.vehicle.slowDown('ego', 0, time_to_stop)
            traci.vehicle.setSpeed('ego', 0)  # Uncomment this line when using step-length of 1s

            # Mark the action as completed and set DATA_COLLECTION_START
            action = True
            DATA_COLLECTION_START = step + int(time_to_stop)  # Set collection time dynamically

def main():
    global DATA_COLLECTION_START
    # Start the SUMO simulation
    traci.start(["sumo", "-c", SUMO_CONFIG])

    # Initialize storage for aggregated data
    interval_data = defaultdict(lambda: defaultdict(list))
    results = defaultdict(list)

    step = 0
    collecting = False
    next_interval_start = None  # Dynamically set when data collection starts

    try:
        while step <= SIMULATION_DURATION:
            traci.simulationStep()

            # Check for ego braking
            if not action:
                ego_brake(step)

            # Start collecting data once DATA_COLLECTION_START is set
            if DATA_COLLECTION_START is not None and step >= DATA_COLLECTION_START:
                collecting = True
                if next_interval_start is None:
                    next_interval_start = DATA_COLLECTION_START

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
            if collecting and step == next_interval_start + TIME_INTERVAL:
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
