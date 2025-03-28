# Description: This script simulates the main flow of the SUMO simulation and computes aggregate flow rates for multiple detectors.

import traci
import matplotlib.pyplot as plt
from collections import deque

DETECTORS = ["E1_0_100m", "E1_1_100m"]  # Replace with the IDs of your detectors
PLOT_WINDOW = 600  # Number of time steps to display in the live plot
AGGREGATE_WINDOW = 300  # Window for aggregate flow rate calculation (in seconds)


def main():
    # Start the SUMO simulation
    traci.start(["sumo", "-c", "2lane.sumocfg"])

    # Initialize data storage for live plotting
    time_steps = deque(maxlen=PLOT_WINDOW)
    flow_rates = {detector: deque(maxlen=PLOT_WINDOW) for detector in DETECTORS}
    aggregate_windows = {detector: deque(maxlen=AGGREGATE_WINDOW) for detector in DETECTORS}
    average_flow_rate = deque(maxlen=PLOT_WINDOW)

    # Set up Matplotlib for live plotting
    plt.ion()  # Interactive mode
    fig, ax = plt.subplots()
    lines = {
        detector: ax.plot([], [], label=f"Flow Rate ({detector})")[0]
        for detector in DETECTORS
    }
    avg_line, = ax.plot([], [], label="Average Flow Rate", linestyle="--", color="black")

    ax.set_xlim(0, PLOT_WINDOW)
    ax.set_ylim(0, 100)  # Adjust y-limit based on expected flow rate
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Flow Rate (vehicles/hour)")
    ax.legend()

    step = 0

    try:
        while step < 1000:  # Run for a fixed number of steps (adjust as needed)
            traci.simulationStep()  # Advance the simulation by one step

            # Update flow rates for each detector
            total_flow = 0
            for detector in DETECTORS:
                # Get the number of vehicles passing the detector in the current step
                vehicles_in_step = traci.inductionloop.getLastStepVehicleNumber(detector)
                aggregate_windows[detector].append(vehicles_in_step)

                # Compute aggregate flow rate for the last AGGREGATE_WINDOW seconds
                total_vehicles = sum(aggregate_windows[detector])
                flow_rate = round(total_vehicles * (3600 / AGGREGATE_WINDOW), 2)  # Convert to vehicles/hour

                # Update data for plotting
                flow_rates[detector].append(flow_rate)
                total_flow += flow_rate

            # Compute average flow rate across all detectors
            avg_flow = total_flow / len(DETECTORS)
            average_flow_rate.append(avg_flow)

            # Update the plot
            time_steps.append(step)
            for detector in DETECTORS:
                lines[detector].set_xdata(time_steps)
                lines[detector].set_ydata(flow_rates[detector])

            # Update average flow rate line
            avg_line.set_xdata(time_steps)
            avg_line.set_ydata(average_flow_rate)

            # Adjust plot limits dynamically
            current_max = max(
                max(max(flow_rates[detector], default=0) for detector in DETECTORS),
                max(average_flow_rate, default=0)
            )
            if current_max > ax.get_ylim()[1]:
                ax.set_ylim(0, current_max + 10)  # Expand y-limit if needed
            ax.set_xlim(max(0, step - PLOT_WINDOW), step)

            plt.draw()
            plt.pause(0.01)  # Pause briefly to update the plot

            step += 1
    except KeyboardInterrupt:
        print("Simulation interrupted.")
    finally:
        traci.close()
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()