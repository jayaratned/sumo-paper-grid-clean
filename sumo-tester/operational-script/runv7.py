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
ROAD_CAPACITY = 2200  # Maximum capacity of the road (veh/h)
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

def main():
    # Load detectors from XML file
    detector_ids = load_detectors_from_xml(DETECTORS_FILE)
    print(f"Loaded detector IDs: {detector_ids}")

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

    # Save results to a CSV file
    save_results_to_csv(results)
    print(f"Simulation complete. Results saved to 'simulation_results.csv'.")

def save_results_to_csv(results):
    """Save the simulation results to a CSV file."""
    df = pd.DataFrame(results)
    df.to_csv("simulation_results.csv", index=False)

if __name__ == "__main__":
    main()
