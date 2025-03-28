# Gets the vehicle count and flow-rate from a detector in consecutive time intervals of same value (e.g., 60 seconds), starting from a specified time (e.g., 10 seconds).
# Tested for simulation step lengths of 0.1s, 1s, 2s.
# Tested for different time intervals
# Tested for vehicles stopped on the detector - flow rate is calculated correctly
# Added a simple 'attack' to stop the ego vehicle on the detector
# Added mean speed calculation for the interval
# Added LOS, SPI, flowrate and mean speed graph plots

import traci
import matplotlib.pyplot as plt

# Simulation configuration
SUMO_CONFIG = "tester.sumocfg"  # SUMO configuration file
DETECTOR_ID = "F0_0_0m"  # E1 detector ID
SIMULATION_DURATION = 1800  # Total simulation time (e.g., 360 seconds)
TIME_INTERVAL = 300  # Time interval to aggregate vehicle counts
INTERVAL_START = 10  # Start time of the interval

# Constants for LOS and SPI calculation
ROAD_CAPACITY = 2200  # Maximum capacity of the road (veh/h)
FREE_FLOW_SPEED = 70  # Free-flow speed (mph)

def determine_los(v_c_ratio):
    """Determine Level of Service (LOS) based on V/C ratio."""
    if 0 <= v_c_ratio <= 0.6:
        return "A", "Free flow"
    elif 0.6 < v_c_ratio <= 0.7:
        return "B", "Stable flow with unaffected speed"
    elif 0.7 < v_c_ratio <= 0.8:
        return "C", "Stable flow but speed is affected"
    elif 0.8 < v_c_ratio <= 0.9:
        return "D", "High-density but stable flow"
    elif 0.9 < v_c_ratio < 1.0:
        return "E", "Near or at capacity with low speed"
    else:
        return "F", "Breakdown flow"
    
def determine_spi(mean_speed):
    """Determine SPI (Speed Performance Index) and traffic state level."""
    spi = mean_speed / FREE_FLOW_SPEED if FREE_FLOW_SPEED > 0 else 0
    if 0 < spi <= 0.25:
        return spi, "Heavy congestion"
    elif 0.25 < spi <= 0.50:
        return spi, "Mild congestion"
    elif 0.50 < spi <= 0.75:
        return spi, "Smooth"
    elif 0.75 < spi <= 1.00:
        return spi, "Very smooth"
    else:
        return spi, "Invalid SPI"

def main():

    total_unique_vehicles = 0  # Total vehicles counted via TraCI
    counted_vehicles = set()  # tracks vehicles that have already been counted
    interval_unique_vehicles = 0  # Vehicles counted in the current interval
    interval_speeds = []  # Speeds of vehicles in the current interval
    interval_start_time = INTERVAL_START  # Start time of the interval

    # Initialize data storage for plotting
    time_intervals = [] # Start time of each interval
    flow_rates = [] # Flow rate for each interval
    mean_speeds = [] # Mean speed for each interval
    los_classes = [] # LOS class for each interval
    spi_values = [] # SPI values for each interval

    traci.start(["sumo", "-c", SUMO_CONFIG]) # Start the SUMO simulation

    while traci.simulation.getTime() < SIMULATION_DURATION:
        traci.simulationStep()

        if 'ego' in traci.vehicle.getIDList():
                if traci.vehicle.getRoadID('ego') == 'F1' and traci.vehicle.getLanePosition('ego') > 6:
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

                # Calculate LOS and SPI
                v_c_ratio = flowrate / ROAD_CAPACITY
                los_class, los_description = determine_los(v_c_ratio)
                spi, spi_description = determine_spi(mean_speed)

                # Store data for plotting
                time_intervals.append(interval_start_time)
                flow_rates.append(flowrate)
                mean_speeds.append(mean_speed)
                los_classes.append(los_class)
                spi_values.append(spi)

                print(
                    f"Interval {interval_start_time}-{current_time}: "
                    f"{interval_unique_vehicles} vehicles, flow rate = {flowrate:.2f} veh/h, "
                    f"mean speed = {mean_speed:.2f} mph, LOS = {los_class} ({los_description}), "
                    f"SPI = {spi:.2f} ({spi_description})"
                )

                # Reset interval data
                interval_unique_vehicles = 0
                interval_speeds.clear()
                interval_start_time += TIME_INTERVAL


    traci.close()

    # Plot the results
    # plot_results(time_intervals, flow_rates, mean_speeds, los_classes, spi_values)
    plot_dashboard(time_intervals, flow_rates, mean_speeds, los_classes, spi_values)

    print(f"Final Total Unique Vehicles: {total_unique_vehicles}")
    

def plot_results(time_intervals, flow_rates, mean_speeds, los_classes, spi_values):
    '''Plot the flow rates, mean speeds, and LOS/SPI over time intervals'''

    plt.figure(figsize=(10, 12))

    # Plot flow rates
    plt.subplot(3, 1, 1)
    plt.plot(time_intervals, flow_rates, marker='o', label='Flow rate (veh/h)', color='blue')
    plt.xlabel('Time interval start (s)')
    plt.ylabel('Flow rate (veh/h)')
    plt.title('Flow rates over time')
    plt.legend()
    plt.grid(True)

    # Plot mean speeds
    plt.subplot(3, 1, 2)
    plt.plot(time_intervals, mean_speeds, marker='o', label='Mean speed (mph)', color='green')
    plt.xlabel('Time interval start (s)')
    plt.ylabel('Mean speed (mph)')
    plt.title('Mean speeds over time')
    plt.legend()
    plt.grid(True)

    # Plot LOS (categorical) and SPI
    plt.subplot(3, 1, 3)
    plt.plot(time_intervals, spi_values, marker='o', label='SPI', color='orange')
    plt.xlabel('Time interval start (s)')
    plt.ylabel('SPI')
    plt.title('SPI (Speed Performance Index) over time')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()

def plot_dashboard(time_intervals, flow_rates, mean_speeds, los_classes, spi_values):
    """Plot a dashboard showing flow rates, mean speeds, SPI, and LOS."""
    plt.figure(figsize=(12, 10))

    # Plot flow rates
    plt.subplot(4, 1, 1)
    plt.plot(time_intervals, flow_rates, marker='o', label='Flow rate (veh/h)', color='blue')
    plt.xticks(time_intervals, labels=[f"{start}-{start + TIME_INTERVAL}" for start in time_intervals], rotation=45)
    plt.xlabel('Time Interval (s)')
    plt.ylabel('Flow Rate (veh/h)')
    plt.title('Flow Rate Over Time')
    plt.legend()
    plt.grid(True)

    # Plot mean speeds
    plt.subplot(4, 1, 2)
    plt.plot(time_intervals, mean_speeds, marker='o', label='Mean Speed (mph)', color='green')
    plt.xticks(time_intervals, labels=[f"{start}-{start + TIME_INTERVAL}" for start in time_intervals], rotation=45)
    plt.xlabel('Time Interval (s)')
    plt.ylabel('Mean Speed (mph)')
    plt.title('Mean Speed Over Time')
    plt.legend()
    plt.grid(True)

    # Plot SPI values
    plt.subplot(4, 1, 3)
    plt.plot(time_intervals, spi_values, marker='o', label='SPI', color='orange')
    plt.xticks(time_intervals, labels=[f"{start}-{start + TIME_INTERVAL}" for start in time_intervals], rotation=45)
    plt.xlabel('Time Interval (s)')
    plt.ylabel('SPI')
    plt.title('Speed Performance Index (SPI) Over Time')
    plt.legend()
    plt.grid(True)

    # Plot LOS classes
    plt.subplot(4, 1, 4)
    los_numeric = [ord(los) - ord('A') + 1 for los in los_classes]  # Convert LOS classes (A-F) to numeric for plotting
    plt.plot(time_intervals, los_numeric, marker='o', label='LOS Class', color='red')
    plt.xticks(time_intervals, labels=[f"{start}-{start + TIME_INTERVAL}" for start in time_intervals], rotation=45)
    plt.yticks(range(1, 7), labels=["A", "B", "C", "D", "E", "F"])
    plt.xlabel('Time Interval (s)')
    plt.ylabel('LOS Class')
    plt.title('Level of Service (LOS) Over Time')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()