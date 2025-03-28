import traci
import time
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import pandas as pd
import csv

# Record the start time
py_start_time = time.time()

ADDITIONAL_FILE = "lanedetectors.add.xml"
second_file = "detectors.add.xml"
DATA_FILE = "data2.csv"
EB_FILE = "emergency_brake2.csv" 
SIMULATION_END_TIME = 1800
TRACKED_VEHICLE_ID = "ego"  # Change this to the vehicle you want to track
SCENARIO = "attack" # Change this to "attack" for the attack scenario or "base" for the base scenario
data = []
eb_log = []
STEP_COUNTER = 1
detector_entry_log = {} # Store vehicles detected in each lane area detector
detector_entry_log1 = {} # Store vehicles detected in each lane area detector
detector_total_counts = {}  # Stores total unique vehicle counts per step
EMERGENCY_BRAKE_THRESHOLD = -4.5  # Threshold for emergency brake detection
COLLISION_FILE = "collision_log2.csv"  # File to save collision data
collision_log = []  # List to store collision events
output_csv_file = "detector_counts.csv"

# Parse XML file to extract lane area detector IDs
tree = ET.parse(ADDITIONAL_FILE)
root = tree.getroot()
lane_detectors = [elem.attrib["id"] for elem in root.findall("laneAreaDetector")]

# Initialize empty sets for each detector
for detector in lane_detectors:
    detector_entry_log[detector] = set()

# Parse XML file to extract lane area detector IDs
tree = ET.parse(second_file)
root = tree.getroot()
e1_detectors = [elem.attrib["id"] for elem in root.findall("e1Detector")]

# Initialize storage dictionaries
for detector1 in e1_detectors:
    detector_entry_log1[detector1] = set()  # Track currently detected vehicles
    detector_total_counts[detector1] = []  # Store unique vehicle counts per step


# Store trajectory data for the tracked vehicle
tracked_vehicle_data = {"distance": [], "speed": []}

def VSL_control():
    """If vehicle type is CAV, set speed limit to 40 mph in E1"""
    for vehicle in traci.vehicle.getIDList():
        if "CAV" in traci.vehicle.getTypeID(vehicle):  # Handles CAV and CAV@xxx types
            if traci.vehicle.getRoadID(vehicle) == "E1":
                traci.vehicle.setMaxSpeed(vehicle, 35 * 0.44704)  # Convert mph to m/s
            else:
                traci.vehicle.setMaxSpeed(vehicle, 55.56)  # Restore default speed


def main():
    """Runs the SUMO simulation and records data"""
    global STEP_COUNTER

    traci.start(["sumo-gui", "-c", "RSU.sumocfg"])

    while traci.simulation.getTime() < SIMULATION_END_TIME:
        traci.simulationStep()

        simtime = traci.simulation.getTime()

        # Collect data every 10 steps (i.e., every 1 second)
        if STEP_COUNTER % 10 == 0:
            data_collection(simtime, SCENARIO)

        # Implement VSL control between t = 300 and t = 2100
        if SCENARIO == "attack":
            if 600 < traci.simulation.getTime() <= 2100:
                VSL_control()

        # Emergency brake detection
        emergency_brake_detection(EMERGENCY_BRAKE_THRESHOLD, SCENARIO)

        # Collision detection
        collision_detection(SCENARIO)

        flowdata_collection(simtime, SCENARIO)

        # Increment step counter per SUMO step
        STEP_COUNTER += 1

    traci.close()

    

def flowdata_collection(simulation_time, scenario_type):
    """Collects vehicle count data from E1 detectors per simulation step."""
    unique_vehicle_count = {}

    for detector1_id in e1_detectors:
        # Get current vehicles on the detector
        detected_vehicles = set(traci.lanearea.getLastStepVehicleIDs(detector1_id))

        # Retrieve previous step's vehicles BEFORE updating
        previous_vehicles = detector_entry_log1.get(detector1_id, set())

        # Identify vehicles that exited (were in last step, but not in this step)
        exited_vehicles = previous_vehicles - detected_vehicles  

        # Store the latest vehicle set for next step comparison (AFTER processing exits)
        detector_entry_log1[detector1_id] = detected_vehicles

        # Store exit count per step
        unique_vehicle_count[detector1_id] = len(exited_vehicles)

        # Append time step and count to detector_total_counts
        detector_total_counts[detector1_id].append((simulation_time, len(exited_vehicles)))

    return unique_vehicle_count  # Returns per-step unique exit counts

def save_detector_counts_to_csv(scenario_type):
    """Saves the unique vehicle count data to a CSV file at the end of the simulation."""
    with open(output_csv_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["detectorID", "time_step", "count", "scenario"])  # Header

        # Iterate over all detectors and their stored counts per timestep
        for detector1_id, counts in detector_total_counts.items():
            for time_step, count in counts:  # Ensure we extract (time_step, count)
                writer.writerow([detector1_id, time_step, count, scenario_type])

    print(f"Detector counts saved to {output_csv_file}")


def data_collection(simulation_time, scenario_type):
    """Collects data from lane area detectors"""
    for detector_id in lane_detectors:
        num_vehicles = traci.lanearea.getLastStepVehicleNumber(detector_id)  # Vehicle count
        mean_speed_mps = traci.lanearea.getLastStepMeanSpeed(detector_id)  # Mean speed (m/s)
        occupancy = traci.lanearea.getLastStepOccupancy(detector_id)  # Occupancy (%)

        detected_vehicles = set(traci.lanearea.getLastStepVehicleIDs(detector_id))  # Get current vehicles
        # Identify vehicles that have exited (were in last step, but not in this step)
        previous_vehicles = detector_entry_log.get(detector_id, set())
        exited_vehicles = previous_vehicles - detected_vehicles
        # Store the latest vehicle set for comparison in the next step
        detector_entry_log[detector_id] = detected_vehicles
        flow = len(exited_vehicles)  # Number of vehicles that exited the detector area

        # Compute density (vehicles per km)
        segment_length_m = 100.0  # Each LAD segment is 100m long
        density_veh_km = (num_vehicles / segment_length_m) * 1000  # Convert to vehicles/km
        
        # Convert speed from m/s to km/h
        mean_speed_kmh = mean_speed_mps * 3.6  # Convert to km/h
        
        # Store data with scenario label
        data.append([simulation_time, detector_id, num_vehicles, flow, density_veh_km, mean_speed_kmh, occupancy, scenario_type])

def emergency_brake_detection(threshold, scenario_type):

    for veh_id in traci.vehicle.getIDList():
        acceleration = traci.vehicle.getAcceleration(veh_id)

        if acceleration < threshold:
            eb_log.append([traci.simulation.getTime(), veh_id, acceleration, traci.vehicle.getSpeed(veh_id), scenario_type])

def collision_detection(scenario_type):
    """Detects and logs collision events"""
    num_collisions = traci.simulation.getCollidingVehiclesNumber()
    colliding_vehicles = traci.simulation.getCollidingVehiclesIDList()

    if num_collisions > 0:
        for veh_id in colliding_vehicles:
            collision_log.append([traci.simulation.getTime(), veh_id, scenario_type])
            print(f"Collision detected: {veh_id} at time {traci.simulation.getTime()}s")


if __name__ == "__main__":
    main()

save_detector_counts_to_csv(SCENARIO)


# Convert to DataFrame
df = pd.DataFrame(data, columns=["Time (s)", "Detector ID", "Vehicle Count", "Exit flow", "Density (veh/km)", "Mean Speed (km/h)", "Occupancy (%)", "Scenario"])
df_ebraking = pd.DataFrame(eb_log, columns=["Time (s)", "Vehicle ID", "Acceleration (m/s^2)", "Speed (m/s)", "Scenario"])
df_collision = pd.DataFrame(collision_log, columns=["Time (s)", "Vehicle ID", "Scenario"])


# Append to CSV (or create if not exists)
try:
    existing_df = pd.read_csv(DATA_FILE)
    df = pd.concat([existing_df, df], ignore_index=True)  # Append new data
except FileNotFoundError:
    print("No existing CSV file found. Creating a new one.")

df.to_csv(DATA_FILE, index=False)
print(f"Data saved to {DATA_FILE}")

# Save emergency brake log
try:
    existing_eb = pd.read_csv(EB_FILE)
    df_eb = pd.concat([existing_eb, df_ebraking], ignore_index=True)  # Append new data
except FileNotFoundError:
    print("No existing emergency brake log found. Creating a new one.")

df_eb.to_csv(EB_FILE, index=False)
print(f"Emergency brake log saved to {EB_FILE}")

# Save to CSV
try:
    existing_collision = pd.read_csv(COLLISION_FILE)
    df_collision = pd.concat([existing_collision, df_collision], ignore_index=True)  # Append new data
except FileNotFoundError:
    print("No existing collision log found. Creating a new one.")

df_collision.to_csv(COLLISION_FILE, index=False)
print(f"Collision log saved to {COLLISION_FILE}")

py_end_time = time.time()
py_elapsed_time = py_end_time - py_start_time
print(f"Script finished in {py_elapsed_time:.2f} seconds.")
