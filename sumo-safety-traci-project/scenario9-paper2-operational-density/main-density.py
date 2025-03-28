import traci
import pandas as pd
import xml.etree.ElementTree as ET
import time
import sys

# Record the start time
py_start_time = time.time()

action = False

def ego_brake():
    global action

    if 'ego' in traci.vehicle.getIDList():
        # Disable safety checks for the 'attack'
        traci.vehicle.setSpeedMode('ego', 0)
        traci.vehicle.setLaneChangeMode('ego', 0)
        time_to_stop = traci.vehicle.getSpeed('ego') / 20 # 9 m/s^2 is the deceleration rate
        traci.vehicle.slowDown('ego', 0, time_to_stop)
        # traci.vehicle.setSpeed('ego', 0) # uncomment this line when using step-length of 1s
        print(f"Ego1 has stopped at time {simulation_time}s.")
        action = True

# Check for scenario type (attack or base)
if len(sys.argv) != 2 or sys.argv[1].lower() not in ["attack", "base"]:
    print("Usage: python script.py <attack/base>")
    sys.exit(1)

scenario_type = sys.argv[1].lower()  # "attack" or "base"
print(f"Running SUMO Simulation: {scenario_type.upper()} Scenario")

# Configuration
SUMO_CMD = ["sumo", "-c", "safety.sumocfg"]  # Replace with your SUMO config file
ADDITIONAL_FILE = "lanedetectors.add.xml"  # Replace with your additional file path
CSV_FILE = "lane_density_speed.csv"
STEP_LENGTH = 0.1  # SUMO simulation step length (seconds)
RECORD_INTERVAL = 1  # Record every 1 second
STEPS_PER_RECORD = int(RECORD_INTERVAL / STEP_LENGTH)  # Every 10 steps

# Parse XML file to extract lane area detector IDs
tree = ET.parse(ADDITIONAL_FILE)
root = tree.getroot()
lane_detectors = [elem.attrib["id"] for elem in root.findall("laneAreaDetector")]

# Initialize data storage
data = []

# Start SUMO
traci.start(SUMO_CMD)

# Simulation loop
simulation_time = 0
step_counter = 0

while traci.simulation.getTime() < 6600:
    traci.simulationStep()  # Advance simulation
    simulation_time = traci.simulation.getTime()

    if int(simulation_time) % 5 == 0:  # Update once every 5 seconds
            print(f"\rCurrent Simulation Time: {simulation_time:.2f}s", end="")
    
    # Only record every 1 second (every 10 steps)
    if step_counter % STEPS_PER_RECORD == 0:
        for detector_id in lane_detectors:
            num_vehicles = traci.lanearea.getLastStepVehicleNumber(detector_id)  # Vehicle count
            mean_speed_mps = traci.lanearea.getLastStepMeanSpeed(detector_id)  # Mean speed (m/s)
            occupancy = traci.lanearea.getLastStepOccupancy(detector_id)  # Occupancy (%)

            # Compute density (vehicles per km)
            segment_length_m = 100.0  # Each LAD segment is 100m long
            density_veh_km = (num_vehicles / segment_length_m) * 1000  # Convert to vehicles/km
            
            # Convert speed from m/s to km/h
            mean_speed_kmh = mean_speed_mps * 3.6  # Convert to km/h
            
            # Store data with scenario label
            data.append([simulation_time, detector_id, num_vehicles, density_veh_km, mean_speed_kmh, occupancy, scenario_type])

    step_counter += 1

    if scenario_type == "attack" and traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 2250 and not action:
        ego_brake()

# Close TraCI
traci.close()

# Convert to DataFrame
df = pd.DataFrame(data, columns=["Time (s)", "Detector ID", "Vehicle Count", "Density (veh/km)", "Mean Speed (km/h)", "Occupancy (%)", "Scenario"])

# Append to CSV (or create if not exists)
try:
    existing_df = pd.read_csv(CSV_FILE)
    df = pd.concat([existing_df, df], ignore_index=True)  # Append new data
except FileNotFoundError:
    print("No existing CSV file found. Creating a new one.")

df.to_csv(CSV_FILE, index=False)

print(f"Data saved to {CSV_FILE}")

py_end_time = time.time()
py_elapsed_time = py_end_time - py_start_time

# Print the elapsed time
print(f"Script finished in {py_elapsed_time:.2f} seconds.")
