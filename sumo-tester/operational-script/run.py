import traci

# Simulation configuration
SUMO_CONFIG = "tester.sumocfg"  # Replace with your SUMO configuration file
DETECTOR_ID = "F0_0_0m"  # Replace with your E1 detector ID
SIMULATION_DURATION = 360  # Total simulation time (e.g., 360 seconds)

def main():
    # Start the SUMO simulation
    traci.start(["sumo-gui", "-c", SUMO_CONFIG])

    total_unique_vehicles = 0  # Total unique vehicles counted via TraCI
    active_vehicles = set()  # Tracks vehicles currently on the detector
    counted_vehicles = set()  # Tracks vehicles that have already been counted

    try:
        while traci.simulation.getTime() <= SIMULATION_DURATION:
            traci.simulationStep()

            if 'ego' in traci.vehicle.getIDList():
                if traci.vehicle.getRoadID('ego') == 'F1' and traci.vehicle.getLanePosition('ego') > 10:
                    # Disable safety checks for the 'attack'
                    traci.vehicle.setSpeedMode('ego', 0)
                    traci.vehicle.setLaneChangeMode('ego', 0)

                    # Calculate time to stop
                    time_to_stop = traci.vehicle.getSpeed('ego') / 9  # Assume deceleration rate of 9 m/s^2
                    traci.vehicle.slowDown('ego', 0, time_to_stop)
                    traci.vehicle.setSpeed('ego', 0)  # Uncomment this line when using step-length of 1s

            try:
                # Get the number of vehicles detected in the last simulation step
                vehicle_ids_on_detector = set(traci.inductionloop.getLastStepVehicleIDs(DETECTOR_ID))

                # Detect new vehicles that have not been counted
                new_vehicles = vehicle_ids_on_detector - counted_vehicles

                # Count and add new vehicles to the counted set
                total_unique_vehicles += len(new_vehicles)
                counted_vehicles.update(new_vehicles)

                # Update active vehicles
                active_vehicles = vehicle_ids_on_detector

                # Print current status
                print(f"Time: {traci.simulation.getTime()}, New Vehicles: {len(new_vehicles)}, Total Unique Vehicles: {total_unique_vehicles}, {vehicle_ids_on_detector}")

            except traci.TraCIException:
                print(f"Warning: Detector '{DETECTOR_ID}' not found.")

    except KeyboardInterrupt:
        print("Simulation interrupted manually.")
    finally:
        traci.close()
        print("Simulation ended.")
        print(f"Final Total Unique Vehicles: {total_unique_vehicles}")

if __name__ == "__main__":
    main()
