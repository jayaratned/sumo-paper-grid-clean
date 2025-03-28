import traci
import xml.etree.ElementTree as ET

# Simulation configuration
SUMO_CONFIG = "tester.sumocfg"  # SUMO configuration file
DETECTORS_FILE = "detectors1.add.xml"  # XML file defining detectors
SIMULATION_DURATION = 3600  # Total simulation time (e.g., 360 seconds)

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

    # Start the SUMO simulation
    traci.start(["sumo-gui", "-c", SUMO_CONFIG])

    # Track last known speed for each detector
    last_known_speeds = {detector_id: 0.0 for detector_id in detector_ids}  # Default to 0.0 m/s


    while traci.simulation.getTime() < SIMULATION_DURATION:
        traci.simulationStep()

        current_time = traci.simulation.getTime()  # Get the current simulation time

        if 'ego' in traci.vehicle.getIDList():
                if traci.vehicle.getRoadID('ego') == 'F1' and traci.vehicle.getLanePosition('ego') > 1000:
                    # Disable safety checks for the 'attack'
                    traci.vehicle.setSpeedMode('ego', 0)
                    traci.vehicle.setLaneChangeMode('ego', 0)

                    # Calculate time to stop
                    time_to_stop = traci.vehicle.getSpeed('ego') / 9  # Assume deceleration rate of 9 m/s^2
                    traci.vehicle.slowDown('ego', 0, time_to_stop)
                    traci.vehicle.setSpeed('ego', 0)  # Uncomment this line when using step-length of 1s

        # Print simulation time
        print(f"\nSimulation Time: {current_time:.2f}s")

        # Iterate over all detectors and process their data
        for detector_id in detector_ids:
            # Get vehicle IDs on the detector for this step
            vehicle_ids_on_detector = traci.inductionloop.getLastStepVehicleIDs(detector_id)

            if vehicle_ids_on_detector:
                # If vehicles are detected, calculate the mean speed and update last known speed
                speeds = [traci.vehicle.getSpeed(vehicle_id) for vehicle_id in vehicle_ids_on_detector]
                mean_speed = sum(speeds) / len(speeds)
                last_known_speeds[detector_id] = mean_speed
            else:
                # If no vehicles are detected, use the last known speed
                mean_speed = last_known_speeds[detector_id]

            # Print detector ID and mean speed
            print(f"  Detector ID: {detector_id}, Mean Speed: {mean_speed:.2f} m/s")

    traci.close()

if __name__ == "__main__":
    main()
