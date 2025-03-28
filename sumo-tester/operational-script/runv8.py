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
# v8: Groups detectors into edges based on their naming convention

import traci
import pandas as pd
import xml.etree.ElementTree as ET

# Simulation configuration
SUMO_CONFIG = "tester.sumocfg"  # SUMO configuration file
DETECTORS_FILE = "detectors.add.xml"  # XML file defining detectors
SIMULATION_DURATION = 1800  # Total simulation time (e.g., 360 seconds)
TIME_INTERVAL = 300  # Time interval to aggregate vehicle counts
INTERVAL_START = 0  # Start time of the interval

# Constants for LOS and SPI calculation
ROAD_CAPACITY = 2200  # Maximum capacity of the road (veh/h per lane)
FREE_FLOW_SPEED = 70  # Free-flow speed (mph)

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
    """Group detectors into edges based on their naming convention."""
    cross_section_map = {}
    for detector_id in detector_ids:
        # Extract edge from the detector ID (e.g., E1_1_1000m -> E1)
        edge = detector_id.split("_")[0]
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
                    "weighted_speed_sum": 0,
                    "lanes": len([k for k, v in cross_section_map.items() if v == cross_section]),
                }

            combined_results[key]["total_vehicles"] += result["interval_unique_vehicles"]
            combined_results[key]["weighted_speed_sum"] += result["mean_speed"] * result["interval_unique_vehicles"]

    cross_section_outputs = []
    for (time, cross_section), data in combined_results.items():
        total_vehicles = data["total_vehicles"]
        mean_speed = data["weighted_speed_sum"] / total_vehicles if total_vehicles > 0 else 0
        flowrate = (total_vehicles * 3600) / TIME_INTERVAL
        road_capacity = ROAD_CAPACITY * data["lanes"]
        v_c_ratio = flowrate / road_capacity
        los_class = determine_los(v_c_ratio)
        spi = determine_spi(mean_speed)

        cross_section_outputs.append({
            "time": time,
            "edge": cross_section,
            "mean_speed": round(mean_speed, 2),
            "flowrate": round(flowrate, 2),
            "LOS": los_class,
            "SPI": round(spi, 2),
            "lanes": data["lanes"],
            "total_vehicles": total_vehicles,
        })

    return cross_section_outputs

def main():
    # Load detectors from XML file
    detector_ids = load_detectors_from_xml(DETECTORS_FILE)

    # Generate cross-section mapping dynamically
    cross_section_map = parse_cross_sections(detector_ids)

    # Initialize data storage for CSV
    results = []

    # Start the SUMO simulation
    traci.start(["sumo", "-c", SUMO_CONFIG])

    # Initialize detector-specific data
    detectors_data = {
        detector_id: {
            "total_unique_vehicles": 0,
            "counted_vehicles": set(),
            "interval_unique_vehicles": 0,
            "interval_speeds": [],
            "interval_start_time": INTERVAL_START,
        }
        for detector_id in detector_ids
    }

    while traci.simulation.getTime() < SIMULATION_DURATION:
        traci.simulationStep()

        if 'ego' in traci.vehicle.getIDList():
                if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 6:
                    # Disable safety checks for the 'attack'
                    traci.vehicle.setSpeedMode('ego', 0)
                    traci.vehicle.setLaneChangeMode('ego', 0)

                    # Calculate time to stop
                    time_to_stop = traci.vehicle.getSpeed('ego') / 9  # Assume deceleration rate of 9 m/s^2
                    traci.vehicle.slowDown('ego', 0, time_to_stop)
                    # traci.vehicle.setSpeed('ego', 0)  # Uncomment this line when using step-length of 1s

        current_time = traci.simulation.getTime()

        # Process each detector
        for detector_id in detector_ids:
            data = detectors_data[detector_id]

            # Start counting only after the specified interval start
            if current_time >= INTERVAL_START:
                vehicle_ids_on_detector = set(traci.inductionloop.getLastStepVehicleIDs(detector_id))

                new_vehicles = vehicle_ids_on_detector - data["counted_vehicles"]

                for vehicle_id in new_vehicles:
                    # Retrieve speed of vehicles (m/s)
                    speed = traci.vehicle.getSpeed(vehicle_id)
                    data["interval_speeds"].append(speed)

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
                    })

                    # Reset interval data
                    data["interval_unique_vehicles"] = 0
                    data["interval_speeds"].clear()
                    data["interval_start_time"] += TIME_INTERVAL

    traci.close()

    # Save individual detector results to a CSV file
    save_results_to_csv(results, "simulation_results.csv")

    # Combine results by cross-section and save to a new CSV file
    cross_section_results = combine_cross_section_outputs(results, cross_section_map)
    save_results_to_csv(cross_section_results, "cross_section_results.csv")

    print(f"Simulation complete. Results saved to 'simulation_results.csv' and 'cross_section_results.csv'.")

def save_results_to_csv(results, filename):
    """Save the simulation results to a CSV file."""
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    main()
