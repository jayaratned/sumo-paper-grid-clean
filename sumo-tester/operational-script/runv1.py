# Gets the vehicle count from a detector in consecutive time intervals of same value (e.g., 60 seconds), starting from a specified time (e.g., 10 seconds).

import traci

# Simulation configuration
SUMO_CONFIG = "tester.sumocfg"  # SUMO configuration file
DETECTOR_ID = "F0_0_0m"  # E1 detector ID
SIMULATION_DURATION = 360  # Total simulation time (e.g., 360 seconds)
TIME_INTERVAL = 60  # Time interval to aggregate vehicle counts
INTERVAL_START = 10  # Start time of the interval

def main():

    total_unique_vehicles = 0  # Total vehicles counted via TraCI
    counted_vehicles = set()  # tracks vehicles that have already been counted
    interval_unique_vehicles = 0  # Vehicles counted in the current interval
    interval_start_time = INTERVAL_START  # Start time of the interval

    traci.start(["sumo", "-c", SUMO_CONFIG]) # Start the SUMO simulation

    while traci.simulation.getTime() < SIMULATION_DURATION:
        traci.simulationStep()

        current_time = traci.simulation.getTime()

        # Start counting only after the specified interval start
        if current_time >= INTERVAL_START: 

            vehicle_ids_on_detector = set(traci.inductionloop.getLastStepVehicleIDs(DETECTOR_ID))

            new_vehicles = vehicle_ids_on_detector - counted_vehicles

            total_unique_vehicles += len(new_vehicles)
            interval_unique_vehicles += len(new_vehicles)
            counted_vehicles.update(new_vehicles)

            # Check if interval has ended
            if current_time >= interval_start_time + TIME_INTERVAL:
                print(f"Interval {interval_start_time}-{current_time}: {interval_unique_vehicles} vehicles")

                # Reset interval count
                interval_unique_vehicles = 0
                interval_start_time += TIME_INTERVAL


            # print(f"Time: {traci.simulation.getTime()}, total = {total_unique_vehicles}")

    traci.close()

if __name__ == "__main__":
    main()