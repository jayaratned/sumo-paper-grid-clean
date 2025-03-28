# Gets the vehicle count and flow-rate from a detector in consecutive time intervals of same value (e.g., 60 seconds), starting from a specified time (e.g., 10 seconds).
# Tested for simulation step lengths of 0.1s, 1s, 2s.
# Tested for different time intervals
# Tested for vehicles stopped on the detector - flow rate is calculated correctly
# Added a simple 'attack' to stop the ego vehicle on the detector
# Added mean speed calculation for the interval
# Added LOS, SPI
# Added save to csv function
# Updated script to handle multiple detectors
# Automatically loads detector IDs from an XML file
# v8:Groups detectors into edges based on their naming convention
# v9: interval start time is set to the ego stop time, updated attack scenario toggle and added scenario column to results
# v10: Added base scenario and shared INTERVAL_START logic between scenarios. Run attack scenario first, then base scenario. add interval start time when running base scenario. Added ego vehicle removal after a specified time.
# v11: Added more precise control of the stopping procedure for the ego vehicle. Added lane change for the ego vehicle to the right lane before stopping. Added lane change mode and speed mode for the ego vehicle. Added lane change to the right lane for the ego vehicle before stopping. Added ego vehicle removal after a specified time.
# runv11.py clone
# run-mainv13.py - updated speed measuring logic

import traci
import pandas as pd
import xml.etree.ElementTree as ET
import time

# Record the start time
py_start_time = time.time()

# Simulation configuration
SUMO_CONFIG = "safety.sumocfg"  # SUMO configuration file
DETECTORS_FILE = "detectors.add.xml"  # XML file defining detectors
SIMULATION_END_TIME = 7200  # Total simulation time (e.g., 360 seconds)
TIME_INTERVAL = 300  # Time interval to aggregate vehicle counts
ATTACK_SCENARIO = False  # Set to True to enable the ego stop logic for attack scenario
INTERVAL_START = 2444.6  # Start time for data collection (shared between scenarios) None if attack scenario is enabled
EGO_BREAKDOWN_DURATION = 36000  # Specify the time in seconds after which the ego vehicle is removed
GUI = "sumo-gui"  # Use "sumo" for headless mode

# Constants for LOS and SPI calculation
ROAD_CAPACITY = 2200  # Maximum capacity of the road (veh/h per lane)
FREE_FLOW_SPEED = 70  # Free-flow speed (mph)

def precise_stop_control(ego_id, target_position, current_speed, current_pos):
    # More precise control of the stopping procedure
    if current_pos < target_position:
        remaining_distance = target_position - current_pos
        deceleration = (current_speed**2) / (2 * remaining_distance)  # Basic physics formula for required deceleration
        time_to_stop = current_speed / deceleration  # Time needed to stop
        return max(0, current_speed - deceleration * traci.simulation.getDeltaT()), time_to_stop
    return 0, 0

def determine_los(v_c_ratio):
    """Determine Level of Service (LOS) based on V/C ratio."""
    if 0 <= v_c_ratio <= 0.6:
        return "A"
    elif 0.6 < v_c_ratio <= 0.7:
        return "B"
    elif 0.7 < v_c_ratio <= 0.8:
        return "C"
    elif 0.8 < v_c_ratio <= 0.9:
        return "D"
    elif 0.9 < v_c_ratio < 1.0:
        return "E"
    else:
        return "F"
    
def determine_spi(mean_speed):
    """Determine SPI (Speed Performance Index)."""
    return mean_speed / FREE_FLOW_SPEED if FREE_FLOW_SPEED > 0 else 0

def load_detectors_from_xml(detectors_file):
    """Load detector IDs from the XML file."""
    tree = ET.parse(detectors_file)
    root = tree.getroot()
    detector_ids = [detector.get("id") for detector in root.findall("e1Detector")]
    return detector_ids

def parse_cross_sections(detector_ids):
    """Group detectors into edges by excluding the middle part of the detector ID."""
    cross_section_map = {}
    for detector_id in detector_ids:
        # Extract edge and position by removing the middle part (e.g., E1_0_1000m -> E1_1000m)
        parts = detector_id.split("_")
        if len(parts) == 3:
            edge = f"{parts[0]}_{parts[2]}"  # Combine the first and last parts
        else:
            edge = detector_id  # Fallback for unexpected formats
        cross_section_map[detector_id] = edge
    return cross_section_map

def combine_cross_section_outputs(results, cross_section_map):
    """Combine outputs for detectors along the same edge for each time interval."""
    combined_results = {}

    for result in results:
        cross_section = cross_section_map.get(result["detector_id"], None)
        time = result["time"]

        if cross_section:
            key = (time, cross_section)
            if key not in combined_results:
                combined_results[key] = {
                    "time": time,
                    "edge": cross_section,
                    "total_vehicles": 0,
                    "detector_speeds": [],  # Store detector mean speeds
                    "lanes": len([k for k, v in cross_section_map.items() if v == cross_section]),
                    "scenario": result["scenario"],
                }

            # Update total vehicle counts for the cross-section
            combined_results[key]["total_vehicles"] += result["interval_unique_vehicles"]
            # Append the mean speed of this detector to the list
            combined_results[key]["detector_speeds"].append(result["mean_speed"])

    cross_section_outputs = []
    for (time, cross_section), data in combined_results.items():
        # Calculate the mean speed as the simple average of detector speeds
        mean_speed = sum(data["detector_speeds"]) / len(data["detector_speeds"]) if data["detector_speeds"] else 0

        # Calculate flowrate as before
        flowrate = (data["total_vehicles"] * 3600) / TIME_INTERVAL
        road_capacity = ROAD_CAPACITY * data["lanes"]
        v_c_ratio = flowrate / road_capacity
        los_class = determine_los(v_c_ratio)
        spi = determine_spi(mean_speed)

        cross_section_outputs.append({
            "time": time,
            "edge": cross_section,
            "mean_speed": round(mean_speed, 2),  # Simple mean of detector speeds
            "flowrate": round(flowrate, 2),  # Flowrate remains unchanged
            "LOS": los_class,
            "SPI": round(spi, 2),
            "lanes": data["lanes"],
            "total_vehicles": data["total_vehicles"],  # Total vehicles from all detectors
            "scenario": data["scenario"],
        })

    return cross_section_outputs

def main():
    global INTERVAL_START

    # Load detectors from XML file
    detector_ids = load_detectors_from_xml(DETECTORS_FILE)

    # Generate cross-section mapping dynamically
    cross_section_map = parse_cross_sections(detector_ids)

    # Initialize variables for ego vehicle stop
    stopFlag = False
    ego_id = 'ego'
    target_lane = '104359041_0'
    target_position = 3001  # Desired position to stop the vehicle on the lane
    ego_stop_time = None

    # New variables for second ego vehicle
    ego2_id = 'ego2'
    target_lane_ego2 = '104359041_1'  # Different lane for ego2
    target_position_ego2 = 3000  # Desired position for ego2 to stop
    ego2_stop_time = None
    ego2_stop_flag = False

    # Start the SUMO simulation
    traci.start([GUI, "-c", SUMO_CONFIG])

    # Initialize data storage for CSV
    results = []

    # Initialize detector-specific data
    detectors_data = {
        detector_id: {
            "total_unique_vehicles": 0,
            "counted_vehicles": set(),
            "interval_unique_vehicles": 0,
            "interval_speeds": [],
            "interval_start_time": 0,
        }
        for detector_id in detector_ids
    }

    while traci.simulation.getTime() < SIMULATION_END_TIME:
        traci.simulationStep()

        current_time = traci.simulation.getTime()

        if int(current_time) % 5 == 0:  # Update once every 5 seconds
            print(f"\rCurrent Simulation Time: {current_time:.2f}s", end="")

        # Ego vehicle 1 stop logic
        if ATTACK_SCENARIO and ego_id in traci.vehicle.getIDList():
            # print(f"Ego1 lane: {traci.vehicle.getLaneID('ego')}, pos: {traci.vehicle.getLanePosition('ego')}")

            if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 2250 and not stopFlag:
                # Disable safety checks for the 'attack'
                traci.vehicle.setSpeedMode('ego', 0)
                traci.vehicle.setLaneChangeMode('ego', 0)
                time_to_stop = traci.vehicle.getSpeed('ego') / 20 # 9 m/s^2 is the deceleration rate
                traci.vehicle.slowDown('ego', 0, time_to_stop)
                # traci.vehicle.setSpeed('ego', 0) # uncomment this line when using step-length of 1s
            
                print(f"Ego1 has stopped at time {current_time}s.")
                stopFlag = True

        # Ego vehicle 2 stop logic
        if ATTACK_SCENARIO and ego2_id in traci.vehicle.getIDList():
            ego2_pos = traci.vehicle.getLanePosition(ego2_id)
            ego2_lane_id = traci.vehicle.getLaneID(ego2_id)

            if ego2_lane_id[:9] == '104359041':
                traci.vehicle.changeLane(ego2_id, 1, 100)  # Ego2 to right lane

            if ego2_lane_id == target_lane_ego2 and not ego2_stop_flag and ego2_pos >= 2900:
                current_speed_ego2 = traci.vehicle.getSpeed(ego2_id)
                new_speed_ego2, time_to_stop_ego2 = precise_stop_control(ego2_id, target_position_ego2, current_speed_ego2, ego2_pos)
                traci.vehicle.setSpeed(ego2_id, new_speed_ego2)

                if abs(ego2_pos - target_position_ego2) <= 1 and not ego2_stop_flag:
                    traci.vehicle.setSpeed(ego2_id, 0)
                    print(f"Ego2 has stopped at time {current_time}s.")
                    ego2_stop_flag = True

        # Check for ego1 stop time and interval start
        if ATTACK_SCENARIO and ego_stop_time is None and ego_id in traci.vehicle.getIDList() and stopFlag:
            ego_stop_time = current_time
            INTERVAL_START = ego_stop_time
            print(f"Ego1 stop time recorded: {ego_stop_time}s.")

        # Check for ego2 stop time and interval start
        if ATTACK_SCENARIO and ego2_stop_time is None and ego2_id in traci.vehicle.getIDList() and ego2_stop_flag:
            ego2_stop_time = current_time
            INTERVAL_START = min(INTERVAL_START, ego2_stop_time) if INTERVAL_START else ego2_stop_time
            print(f"Ego2 stop time recorded: {ego2_stop_time}s.")

        # Remove ego1 after breakdown duration
        if ego_id in traci.vehicle.getIDList() and INTERVAL_START is not None and current_time >= EGO_BREAKDOWN_DURATION + INTERVAL_START:
            traci.vehicle.remove(ego_id)
            print(f"Ego1 removed at time: {current_time}s.")

        # Remove ego2 after breakdown duration
        if ego2_id in traci.vehicle.getIDList() and INTERVAL_START is not None and current_time >= EGO_BREAKDOWN_DURATION + INTERVAL_START:
            traci.vehicle.remove(ego2_id)
            print(f"Ego2 removed at time: {current_time}s.")

        # Process each detector
        for detector_id in detector_ids:
            data = detectors_data[detector_id]

            # Start counting only after the INTERVAL_START
            if INTERVAL_START is not None and current_time >= INTERVAL_START:
                if data["interval_start_time"] == 0:
                    data["interval_start_time"] = INTERVAL_START

                vehicle_ids_on_detector = set(traci.inductionloop.getLastStepVehicleIDs(detector_id))

                new_vehicles = vehicle_ids_on_detector - data["counted_vehicles"]

                vehicle_ids_on_detector = set(traci.inductionloop.getLastStepVehicleIDs(detector_id))
                new_vehicles = vehicle_ids_on_detector - data["counted_vehicles"]

                for vehicle_id in new_vehicles:
                    if vehicle_id in traci.vehicle.getIDList():  # Ensure the vehicle still exists
                        try:
                            speed = traci.vehicle.getSpeed(vehicle_id)
                            data["interval_speeds"].append(speed)
                        except traci.TraCIException:
                            print(f"Warning: Vehicle {vehicle_id} no longer exists. Skipping speed retrieval.")
                    else:
                        print(f"Warning: Vehicle {vehicle_id} was removed before accessing speed. Skipping.")


                # for vehicle_id in new_vehicles:
                #     # Retrieve speed of vehicles (m/s)
                #     speed = traci.vehicle.getSpeed(vehicle_id)
                #     data["interval_speeds"].append(speed)

                data["total_unique_vehicles"] += len(new_vehicles)
                data["interval_unique_vehicles"] += len(new_vehicles)
                data["counted_vehicles"].update(new_vehicles)

                # Check if interval has ended
                if current_time >= data["interval_start_time"] + TIME_INTERVAL:
                    # Calculate flow rate
                    flowrate = data["interval_unique_vehicles"] * 3600 / TIME_INTERVAL

                    # Calculate mean speed (convert to mph)
                    if data["interval_speeds"]:
                        mean_speed = sum(data["interval_speeds"]) / len(data["interval_speeds"]) * 2.23694
                    else:
                        mean_speed = 0.0

                    # Calculate LOS and SPI
                    v_c_ratio = flowrate / ROAD_CAPACITY
                    los_class = determine_los(v_c_ratio)
                    spi = determine_spi(mean_speed)

                    # Append results for this interval
                    results.append({
                        "time": data["interval_start_time"],
                        "detector_id": detector_id,
                        "mean_speed": round(mean_speed, 2),
                        "flowrate": round(flowrate, 2),
                        "LOS": los_class,
                        "SPI": round(spi, 2),
                        "time_interval": TIME_INTERVAL,
                        "interval_unique_vehicles": data["interval_unique_vehicles"],
                        "scenario": "attack" if ATTACK_SCENARIO else "base",
                    })

                    # Reset interval data
                    data["interval_unique_vehicles"] = 0
                    data["interval_speeds"].clear()
                    data["interval_start_time"] += TIME_INTERVAL

    traci.close()

    # Combine results by cross-section and append to the same file
    cross_section_results = combine_cross_section_outputs(results, cross_section_map)
    handle_file_operations(results, cross_section_results, ATTACK_SCENARIO)

def save_results_to_csv(results, filename, append=False):
    """Save or append the simulation results to a CSV file."""
    df = pd.DataFrame(results)
    if append:
        df.to_csv(filename, mode='a', header=False, index=False)
    else:
        df.to_csv(filename, index=False)

def handle_file_operations(results, cross_section_results, attack_scenario):
    """Handle file operations based on the scenario."""
    detector_results_filename = "detector_results.csv"
    cross_section_results_filename = "cross_section_results.csv"

    # Save or append individual detector results
    save_results_to_csv(results, detector_results_filename, append=not attack_scenario)

    # Save or append cross-section results
    save_results_to_csv(cross_section_results, cross_section_results_filename, append=not attack_scenario)

    if attack_scenario:
        print(f"Attack scenario results saved to '{detector_results_filename}' and '{cross_section_results_filename}'.")
    else:
        print(f"Base scenario results appended to '{detector_results_filename}' and '{cross_section_results_filename}'.")

if __name__ == "__main__":
    main()

py_end_time = time.time()
py_elapsed_time = py_end_time - py_start_time

# Print the elapsed time
print(f"Script finished in {py_elapsed_time:.2f} seconds.")
