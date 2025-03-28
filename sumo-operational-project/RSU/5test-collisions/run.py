import traci
import time
import xml.etree.ElementTree as ET
import random
import pandas as pd
import shutil
import os

# Generate 5 unique random seeds between 1 and 23423
num_seeds = 5
seeds = random.sample(range(1, 23424), num_seeds)

print("Generated random seeds:", seeds)

SIMULATION_END_TIME = 400
scenarios = ["attack", "base"]
ADDITIONAL_FILE = "lanedetectors.add.xml"
EMERGENCY_BRAKE_THRESHOLD = -4.5

os.makedirs("e1", exist_ok=True)

# Parse lane area detectors once globally
tree = ET.parse(ADDITIONAL_FILE)
root = tree.getroot()
lane_detectors = [elem.attrib["id"] for elem in root.findall("laneAreaDetector")]

def VSL_control_ebraking():
    """If vehicle type is CAV, set speed limit to 40 mph in E1"""
    for vehicle in traci.vehicle.getIDList():
        print(f"vehicle speed: {traci.vehicle.getSpeed(vehicle) * 2.23694} mph, location: {traci.vehicle.getLanePosition(vehicle)}")
        if "CAV" in traci.vehicle.getTypeID(vehicle):  # Handles CAV and CAV@xxx types
            if traci.vehicle.getLanePosition(vehicle) > 3000 and traci.vehicle.getLanePosition(vehicle) < 4000:
                traci.vehicle.setMaxSpeed(vehicle, 35 * 0.44704)  # Convert mph to m/s
                
            else:
                traci.vehicle.setMaxSpeed(vehicle, 55.56)  # Restore default speed 

def VSL_control(VSL):
    """Gradually slow down CAVs in E1 within a specific location range using dynamic deceleration"""
    MAX_DECELERATION = -3.0  # Maximum desired deceleration rate in m/s² (adjustable)
    
    for vehicle in traci.vehicle.getIDList():
        current_speed = traci.vehicle.getSpeed(vehicle)  # Current speed (m/s)
        current_position = traci.vehicle.getLanePosition(vehicle)  # Vehicle position on the lane

        # print(f"Vehicle: {vehicle}, Speed: {current_speed * 2.23694:.2f} mph, Position: {current_position:.2f} m")

        if "CAV" in traci.vehicle.getTypeID(vehicle):  # Handles CAV and CAV@xxx types
            if 3000 < current_position < 4000:
                target_speed = VSL * 0.44704  # Convert mph to m/s
                
                # Check if the vehicle needs to slow down
                if current_speed > target_speed:
                    # Compute required deceleration time
                    deceleration_time = (current_speed - target_speed) / abs(MAX_DECELERATION)
                    
                    # Ensure a minimum time threshold to avoid excessive deceleration
                    # deceleration_time = max(deceleration_time, 1.0)  # At least 1 second

                    # Issue slow down command
                    traci.vehicle.slowDown(vehicle, target_speed, deceleration_time)  
                    slowing_vehicles[vehicle] = target_speed  # Mark vehicle as slowing down
                    # print(f"Slowing down {vehicle} to {target_speed * 2.23694:.2f} mph over {deceleration_time:.2f} sec")
                
                else:
                    # Vehicle has reached the target speed, keep it there
                    traci.vehicle.setMaxSpeed(vehicle, target_speed)
                    # print(f"{vehicle} maintaining speed of {target_speed * 2.23694:.2f} mph")
            
            else:
                # Restore original max speed when leaving the zone
                traci.vehicle.setMaxSpeed(vehicle, 55.56)  # Restore default speed
                if vehicle in slowing_vehicles:
                    del slowing_vehicles[vehicle]  # Remove from tracking once out of the zone

def ego_brake():
    """Selects one CAV vehicle and applies emergency braking at a predefined position."""
    global attack_success, CAV_detected, chosen_vehicle

    vehicle_type_to_pick = "CAV"
    lane_id = 'E0_0'
    detection_position_min = 3000
    detection_position_max = 3490
    emergency_decel = 9.0
    stop_position = 3500

    # Once braking has been executed, do nothing further
    if attack_success:
        return

    # Detect and store one CAV vehicle if none has been selected yet
    if not CAV_detected:
        vehicles_in_lane = traci.lane.getLastStepVehicleIDs(lane_id)
        eligible_vehicles = [veh_id for veh_id in vehicles_in_lane 
                             if vehicle_type_to_pick in traci.vehicle.getTypeID(veh_id) 
                             and detection_position_min <= traci.vehicle.getLanePosition(veh_id) <= detection_position_max]

        if eligible_vehicles:
            chosen_vehicle = random.choice(eligible_vehicles)
            CAV_detected = True
            print(f"Selected vehicle for emergency braking: {chosen_vehicle}")

    # If a vehicle has been detected, track its position and apply braking at stop_position
    if CAV_detected and chosen_vehicle in traci.vehicle.getIDList():
        veh_pos = traci.vehicle.getLanePosition(chosen_vehicle)
        if veh_pos >= stop_position:
            current_speed = traci.vehicle.getSpeed(chosen_vehicle)
            stopping_time = current_speed / emergency_decel
            traci.vehicle.slowDown(chosen_vehicle, speed=0.0, duration=stopping_time)
            traci.vehicle.setSpeed(chosen_vehicle, 0.0)
            attack_success = True  # braking completed
            print(f"Emergency braking applied to {chosen_vehicle} at position {veh_pos:.2f}m, speed {current_speed * 2.23694:.2f} mph")

    elif CAV_detected and chosen_vehicle not in traci.vehicle.getIDList():
        print("Chosen vehicle has left the simulation without braking.")
        attack_success = True  # Prevent further tracking

def brake_check():
    global switch
    """
    Applies emergency braking to all vehicles of type 'CAV' currently in the simulation.
    
    Parameters:
        emergency_decel (float): Emergency braking deceleration rate (m/s²). Default is 9.0.
    """
    if not switch:
        vehicles = traci.vehicle.getIDList()
        cav_vehicles = [veh_id for veh_id in vehicles if "CAV" in traci.vehicle.getTypeID(veh_id)]

        for veh_id in cav_vehicles:
            current_speed = traci.vehicle.getSpeed(veh_id)
            traci.vehicle.setSpeedMode(veh_id, 0)
            traci.vehicle.setLaneChangeMode(veh_id, 0)
            stopping_time = current_speed / 9.0  # Emergency braking deceleration rate
            traci.vehicle.slowDown(veh_id, speed=0.0, duration=stopping_time)
            traci.vehicle.setSpeed(veh_id, 0.0)

            print(f"Emergency braking applied to vehicle {veh_id} at {current_speed * 2.23694:.2f} mph.")
        switch = True



for scenario in scenarios:
    for seed in seeds:
        print(f"Running scenario: {scenario}, seed: {seed}")

        data, eb_log, collision_log = [], [], []
        detector_entry_log = {detector: set() for detector in lane_detectors}
        slowing_vehicles = {}
        CAV_detected = False
        attack_success = False
        chosen_vehicle = None
        switch = False
        STEP_COUNTER = 1

        # Prepare unique XML file for e1 detectors
        original_xml = "e1detectors.add.xml"
        modified_xml = f"e1detectors_{scenario}_{seed}.add.xml"
        shutil.copy(original_xml, modified_xml)

        # Modify XML detector output filename
        tree = ET.parse(modified_xml)
        root = tree.getroot()
        for elem in root.findall("e1Detector"):
            elem.set("file", f"e1/e1detectors_{scenario}_{seed}.xml")
        tree.write(modified_xml)

        # Start SUMO
        sumoCmd = [
            "sumo-gui",
            "-c", "RSU.sumocfg",
            "--seed", str(seed),
            "--additional-files", f"{modified_xml},{ADDITIONAL_FILE}"
        ]
        traci.start(sumoCmd)

        while traci.simulation.getTime() < SIMULATION_END_TIME:
            traci.simulationStep()
            simtime = traci.simulation.getTime()

            # Data collection every second
            if STEP_COUNTER % 10 == 0:
                for detector_id in lane_detectors:
                    num_vehicles = traci.lanearea.getLastStepVehicleNumber(detector_id)

                    density_veh_km = (num_vehicles / 100.0) * 1000

                    data.append([simtime, detector_id, num_vehicles, density_veh_km, scenario, seed])

            # VSL and Attack scenario handling
            if scenario == "attack":
                if simtime > 300:
                    brake_check()

            # Emergency brake detection
            for veh_id in traci.vehicle.getIDList():
                acceleration = traci.vehicle.getAcceleration(veh_id)
                if acceleration < EMERGENCY_BRAKE_THRESHOLD:
                    eb_log.append([simtime, veh_id, acceleration,
                                   traci.vehicle.getSpeed(veh_id)*2.23694,
                                   traci.vehicle.getLanePosition(veh_id), scenario, seed])

            # Collision detection
            collisions = traci.simulation.getCollisions()
            for collision in collisions:
                collision_log.append([
                    simtime,
                    collision.collider,
                    collision.victim,
                    collision.colliderType,
                    collision.victimType,
                    collision.colliderSpeed * 2.23694,
                    collision.victimSpeed * 2.23694,
                    collision.lane,
                    collision.pos,
                    scenario,
                    seed
                ])

            STEP_COUNTER += 1

        traci.close()

        # Ensure directories exist
        os.makedirs("data", exist_ok=True)
        os.makedirs("emergency", exist_ok=True)
        os.makedirs("collision", exist_ok=True)

        # Saving data after each run
        df = pd.DataFrame(data, columns=["Time (s)", "Detector ID", "Vehicle Count", "Density (veh/km)", "Scenario", "Seed"])
        df.to_csv(f"data/data_{scenario}_{seed}.csv", index=False)

        df_ebraking = pd.DataFrame(eb_log, columns=["Time (s)", "Vehicle ID", "Acceleration (m/s^2)",
                                                    "Speed (mph)", "Position", "Scenario", "Seed"])
        df_ebraking.to_csv(f"emergency/emergency_brake_{scenario}_{seed}.csv", index=False)

        df_collision = pd.DataFrame(collision_log, columns=["Time (s)", "Collider ID", "Victim ID", "Collider Type",
                                                            "Victim Type", "Collider Speed (mph)", "Victim Speed (mph)",
                                                            "Lane", "Position (m)", "Scenario", "Seed"])
        df_collision.to_csv(f"collision/collision_log_{scenario}_{seed}.csv", index=False)

        # Delete additional files
        os.remove(modified_xml)

        print(f"Completed scenario: {scenario}, seed: {seed}")




