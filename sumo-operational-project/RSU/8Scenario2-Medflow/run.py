import traci
import time
import xml.etree.ElementTree as ET
import random
import pandas as pd
import shutil
import os

# Record the start time
py_start_time = time.time()

# Generate unique random seeds between 1 and 23423
num_seeds = 5
seeds = random.sample(range(1, 23424), num_seeds)

print("Generated random seeds:", seeds)

SIMULATION_END_TIME = 7800
scenarios = ["attack", "base"]
ADDITIONAL_FILE = "lanedetectors.add.xml"
EMERGENCY_BRAKE_THRESHOLD = -4.5

os.makedirs("e1", exist_ok=True)

# Parse lane area detectors once globally
tree = ET.parse(ADDITIONAL_FILE)
root = tree.getroot()
lane_detectors = [elem.attrib["id"] for elem in root.findall("laneAreaDetector")]

def VSL_control_ebraking(VSL):
    """If vehicle type is CAV, set speed limit to 40 mph in E1"""
    for vehicle in traci.vehicle.getIDList():
        # print(f"vehicle speed: {traci.vehicle.getSpeed(vehicle) * 2.23694} mph, location: {traci.vehicle.getLanePosition(vehicle)}")
        if "CAV" in traci.vehicle.getTypeID(vehicle):  # Handles CAV and CAV@xxx types
            if traci.vehicle.getLanePosition(vehicle) > 3000 and traci.vehicle.getLanePosition(vehicle) < 4000:
                traci.vehicle.setMaxSpeed(vehicle, VSL * 0.44704)  # Convert mph to m/s
                
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
            traci.vehicle.setSpeedMode(chosen_vehicle, 0)
            traci.vehicle.setLaneChangeMode(chosen_vehicle, 0)
            current_speed = traci.vehicle.getSpeed(chosen_vehicle)
            # stopping_time = current_speed / emergency_decel
            # traci.vehicle.slowDown(chosen_vehicle, speed=0.0, duration=stopping_time)
            traci.vehicle.setSpeed(chosen_vehicle, 0.0)
            attack_success = True  # braking completed
            print(f"Emergency braking applied to {chosen_vehicle} at position {veh_pos:.2f}m, speed {current_speed * 2.23694:.2f} mph")

    elif CAV_detected and chosen_vehicle not in traci.vehicle.getIDList():
        print("Chosen vehicle has left the simulation without braking.")
        attack_success = True  # Prevent further tracking

def ego_acceleration():
    """Selects a CAV vehicle and aggressively accelerates it until collision with leader vehicle. not fully functional yet"""
    global attack_success, CAV_detected, chosen_vehicle

    vehicle_type_to_pick = "CAV"
    lane_id = 'E0_0'
    detection_position_min = 3000
    detection_position_max = 3490
    acceleration_position = 3500
    aggressive_acceleration = 5.0  # Aggressive yet realistic acceleration (m/s²)

    if attack_success:
        return

    # Detect and select one vehicle if not already done
    if not CAV_detected:
        vehicles_in_lane = traci.lane.getLastStepVehicleIDs(lane_id)
        eligible_vehicles = [
            veh_id for veh_id in vehicles_in_lane
            if vehicle_type_to_pick in traci.vehicle.getTypeID(veh_id)
            and detection_position_min <= traci.vehicle.getLanePosition(veh_id) <= detection_position_max
        ]

        if eligible_vehicles:
            chosen_vehicle = random.choice(eligible_vehicles)
            CAV_detected = True
            print(f"Vehicle selected for aggressive collision scenario: {chosen_vehicle}")

    # Continuously track the selected vehicle and initiate aggressive acceleration
    if CAV_detected and chosen_vehicle in traci.vehicle.getIDList():
        veh_pos = traci.vehicle.getLanePosition(chosen_vehicle)

        if veh_pos >= acceleration_position:
            # Disable all safety checks to ensure collision
            traci.vehicle.setSpeedMode(chosen_vehicle, 0)
            traci.vehicle.setLaneChangeMode(chosen_vehicle, 0)

            # Continuously apply acceleration until collision happens
            leader_data = traci.vehicle.getLeader(chosen_vehicle, 250)
            if leader_data:
                leader_id, distance_to_leader = leader_data
                traci.vehicle.setAcceleration(chosen_vehicle, aggressive_acceleration, 1)  # accelerate continuously every timestep
                
                # Check for collision (SUMO built-in)
                collisions = traci.simulation.getCollisions()
                collided = any(collision.collider == chosen_vehicle and collision.victim == leader_id for collision in collisions)
                
                if collided or distance_to_leader <= 0.5:  # collision or very close
                    traci.vehicle.setAcceleration(chosen_vehicle, 0, 0)
                    traci.vehicle.setSpeed(chosen_vehicle, 0)
                    traci.vehicle.setSpeedMode(chosen_vehicle, -1)
                    traci.vehicle.setLaneChangeMode(chosen_vehicle, -1)
                    
                    traci.vehicle.setSpeed(leader_id, 0)
                    traci.vehicle.setSpeedMode(leader_id, -1)
                    traci.vehicle.setLaneChangeMode(leader_id, -1)
                    
                    attack_success = True
                    print(f"Collision occurred between {chosen_vehicle} and {leader_id}. Both vehicles stopped.")

            else:
                print("No leader vehicle found ahead within 250m.")
        else:
            print(f"Waiting for {chosen_vehicle} to reach acceleration position ({acceleration_position}m). Current position: {veh_pos:.2f}m.")

    elif CAV_detected and chosen_vehicle not in traci.vehicle.getIDList():
        print("Chosen vehicle exited the simulation without collision.")
        attack_success = True

for scenario in scenarios:
    for seed in seeds:
        print(f"Running scenario: {scenario}, seed: {seed}")

        data, eb_log, collision_log = [], [], []
        detector_entry_log = {detector: set() for detector in lane_detectors}
        slowing_vehicles = {}
        CAV_detected = False
        attack_success = False
        chosen_vehicle = None
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
            "sumo",
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
                if 600 < simtime <= 2400:
                    VSL_control_ebraking(50)
                elif 2400 < simtime <= 4200:
                    VSL_control_ebraking(40)
                elif 4200 < simtime <= 7800:
                    VSL_control_ebraking(30)

                if simtime >= 6000 and not attack_success:
                    ego_brake()

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

py_end_time = time.time()
py_elapsed_time = py_end_time - py_start_time
print(f"Script finished in {py_elapsed_time:.2f} seconds.")




