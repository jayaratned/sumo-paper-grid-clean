# Gets the vehicle count and flow-rate from a detector in consecutive time intervals of same value (e.g., 60 seconds), starting from a specified time (e.g., 10 seconds).
# Tested for simulation step lengths of 0.1s, 1s, 2s.
# Tested for different time intervals
# Tested for vehicles stopped on the detector - flow rate is calculated correctly
# Added a simple 'attack' to stop the ego vehicle on the detector
# Added mean speed calculation for the interval


import traci

# Simulation configuration
SUMO_CONFIG = "tester.sumocfg"  # SUMO configuration file
DETECTOR_ID = "F0_0_0m"  # E1 detector ID
SIMULATION_DURATION = 3600  # Total simulation time (e.g., 360 seconds)
TIME_INTERVAL = 60  # Time interval to aggregate vehicle counts
INTERVAL_START = 0  # Start time of the interval

def main():

    total_unique_vehicles = 0  # Total vehicles counted via TraCI
    counted_vehicles = set()  # tracks vehicles that have already been counted
    interval_unique_vehicles = 0  # Vehicles counted in the current interval
    interval_speeds = []  # Speeds of vehicles in the current interval
    interval_start_time = INTERVAL_START  # Start time of the interval

    traci.start(["sumo-gui", "-c", SUMO_CONFIG]) # Start the SUMO simulation

    while traci.simulation.getTime() < SIMULATION_DURATION:
        traci.simulationStep()

        if 'ego' in traci.vehicle.getIDList():
                if traci.vehicle.getRoadID('ego') == 'F1' and traci.vehicle.getLanePosition('ego') > 1000:
                    # Disable safety checks for the 'attack'
                    traci.vehicle.setSpeedMode('ego', 0)
                    traci.vehicle.setLaneChangeMode('ego', 0)

                    # Calculate time to stop
                    time_to_stop = traci.vehicle.getSpeed('ego') / 9  # Assume deceleration rate of 9 m/s^2
                    traci.vehicle.slowDown('ego', 0, time_to_stop)
                    traci.vehicle.setSpeed('ego', 0)  # Uncomment this line when using step-length of 1s

        current_time = traci.simulation.getTime()

        # Start counting only after the specified interval start
        if current_time >= INTERVAL_START: 

            vehicle_ids_on_detector = set(traci.inductionloop.getLastStepVehicleIDs(DETECTOR_ID))

            new_vehicles = vehicle_ids_on_detector - counted_vehicles

            for vehicle_id in new_vehicles:
                # Retreive speed of vehicles (m/s)
                speed = traci.vehicle.getSpeed(vehicle_id)
                interval_speeds.append(speed)


            total_unique_vehicles += len(new_vehicles)
            interval_unique_vehicles += len(new_vehicles)
            counted_vehicles.update(new_vehicles)

            # Check if interval has ended
            if current_time >= interval_start_time + TIME_INTERVAL:
                # Calculate flow rate
                flowrate = interval_unique_vehicles * 3600 / TIME_INTERVAL

                # Calculate mean speed (convert to mph)
                if interval_speeds:
                    mean_speed = sum(interval_speeds) / len(interval_speeds) * 2.23694
                else:
                    mean_speed = 0.0

                print(
                    f"Interval {interval_start_time}-{current_time}: "
                    f"{interval_unique_vehicles} vehicles, flow rate = {flowrate:.2f} vehicles/hour, "
                    f"mean speed = {mean_speed:.2f} mph"
                )

                # Reset interval data
                interval_unique_vehicles = 0
                interval_speeds.clear()
                interval_start_time += TIME_INTERVAL


    traci.close()
    print(f"Final Total Unique Vehicles: {total_unique_vehicles}")

if __name__ == "__main__":
    main()