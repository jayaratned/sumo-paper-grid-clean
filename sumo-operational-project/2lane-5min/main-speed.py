# Description: This script simulates the SUMO simulation and computes mean speeds (in mph) for multiple detectors.

import traci
import matplotlib.pyplot as plt
from collections import deque

DETECTORS = ["E1_0_100m", "E1_1_100m"]  # Replace with the IDs of your detectors
PLOT_WINDOW = 600  # Number of time steps to display in the live plot
AGGREGATE_WINDOW = 300  # Window for aggregate mean speed calculation (in seconds)
MPS_TO_MPH = 2.23694  # Conversion factor: meters/second to miles/hour


def main():
    # Start the SUMO simulation
    traci.start(["sumo", "-c", "2lane.sumocfg"])

    # Initialize data storage for live plotting
    time_steps = deque(maxlen=PLOT_WINDOW)
    mean_speeds = {detector: deque(maxlen=PLOT_WINDOW) for detector in DETECTORS}
    aggregate_windows = {detector: deque(maxlen=AGGREGATE_WINDOW) for detector in DETECTORS}
    average_mean_speed = deque(maxlen=PLOT_WINDOW)

    # Set up Matplotlib for live plotting
    plt.ion()  # Interactive mode
    fig, ax = plt.subplots()
    lines = {
        detector: ax.plot([], [], label=f"Mean Speed ({detector})")[0]
        for detector in DETECTORS
    }
    avg_line, = ax.plot([], [], label="Average Mean Speed", linestyle="--", color="black")

    ax.set_xlim(0, PLOT_WINDOW)
    ax.set_ylim(0, 60)  # Adjust y-limit for speeds in mph (default range: 0 to 60 mph)
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Mean Speed (mph)")
    ax.legend()

    step = 0

    try:
        while step < 1000:  # Run for a fixed number of steps (adjust as needed)
            traci.simulationStep()  # Advance the simulation by one step

            # Update mean speeds for each detector
            total_speed = 0
            valid_detectors = 0  # Count detectors with valid speed readings
            for detector in DETECTORS:
                # Get the mean speed of vehicles passing the detector in the current step
                mean_speed_mps = traci.inductionloop.getLastStepMeanSpeed(detector)
                mean_speed_mph = mean_speed_mps * MPS_TO_MPH  # Convert to mph
                aggregate_windows[detector].append(mean_speed_mph)

                # Compute aggregate mean speed for the last AGGREGATE_WINDOW seconds
                avg_speed_window = sum(aggregate_windows[detector]) / len(aggregate_windows[detector])
                mean_speeds[detector].append(round(avg_speed_window, 2))

                # Update total for average calculation
                if avg_speed_window > 0:  # Only consider valid speeds
                    total_speed += avg_speed_window
                    valid_detectors += 1

            # Compute average mean speed across all detectors
            avg_speed = total_speed / valid_detectors if valid_detectors > 0 else 0
            average_mean_speed.append(round(avg_speed, 2))

            # Update the plot
            time_steps.append(step)
            for detector in DETECTORS:
                lines[detector].set_xdata(time_steps)
                lines[detector].set_ydata(mean_speeds[detector])

            # Update average mean speed line
            avg_line.set_xdata(time_steps)
            avg_line.set_ydata(average_mean_speed)

            # Adjust plot limits dynamically
            current_max = max(
                max(max(mean_speeds[detector], default=0) for detector in DETECTORS),
                max(average_mean_speed, default=0)
            )
            if current_max > ax.get_ylim()[1]:
                ax.set_ylim(0, current_max + 5)  # Expand y-limit if needed
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
