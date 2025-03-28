import traci
import matplotlib.pyplot as plt
import sys

var = sys.argv[1]


# Start TraCI
traci.start(["sumo", "-c", "safety.sumocfg"])

ego_speeds = []
times = []
step = 0

action = False

def base():
    # global action

    # if 'ego' in traci.vehicle.getIDList():
    #     if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 2250 and not action:
    #         # Disable safety checks for the 'attack'
    #         traci.vehicle.setSpeedMode('ego', 0)
    #         traci.vehicle.setLaneChangeMode('ego', 0)
    #         time_to_stop = traci.vehicle.getSpeed('ego') / 20 # 9 m/s^2 is the deceleration rate
    #         traci.vehicle.slowDown('ego', 0, time_to_stop)
    #         # traci.vehicle.setSpeed('ego', 0) # uncomment this line when using step-length of 1s
    #         action = True
    return 0

def ego_brake():
    global action

    if 'ego' in traci.vehicle.getIDList():
        if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 2250 and not action:
            # Disable safety checks for the 'attack'
            traci.vehicle.setSpeedMode('ego', 0)
            traci.vehicle.setLaneChangeMode('ego', 0)
            time_to_stop = traci.vehicle.getSpeed('ego') / 20 # 9 m/s^2 is the deceleration rate
            traci.vehicle.slowDown('ego', 0, time_to_stop)
            # traci.vehicle.setSpeed('ego', 0) # uncomment this line when using step-length of 1s
            action = True

def ego_lanechange():
    global action

    if 'ego' in traci.vehicle.getIDList():
        if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 1000 and not action:
            # Disable safety checks for the 'attack'
            traci.vehicle.setSpeedMode('ego', 0)
            traci.vehicle.setLaneChangeMode('ego', 0)

            current_lane = int(traci.vehicle.getLaneID('ego').split('_')[1])
            print('Changing lane, current lane:', current_lane)
            target_lane = 0 if current_lane == 1 else 1
            traci.vehicle.changeLane('ego', target_lane, 100)
            action = True


def ego_acceleration():
    global action

    if 'ego' in traci.vehicle.getIDList():
        if traci.vehicle.getRoadID('ego') == 'E1':
            leader_id, distance_to_leader = traci.vehicle.getLeader('ego', 100)  # Looks up to 100 meters ahead
            print('leader_id:', leader_id, 'distance_to_leader:', distance_to_leader)

        if traci.vehicle.getRoadID('ego') == 'E1' and traci.vehicle.getLanePosition('ego') > 2250 and not action:
            # Disable safety checks for the 'attack'
            traci.vehicle.setSpeedMode('ego', 0)
            traci.vehicle.setLaneChangeMode('ego', 0)
            traci.vehicle.setAcceleration('ego', 5, 2.875) # moves past the leader

            if distance_to_leader < 10:
                traci.vehicle.setSpeedMode('ego', -1)
                traci.vehicle.setLaneChangeMode('ego', -1)
                traci.vehicle.setSpeed('ego', -1)

            action = True

def ego_acceleration_and_lanechange():
    traci.vehicle.changeLaneRelative('attack', 1, 100)
    traci.vehicle.setSpeed('attack', 13.89)
    traci.vehicle.setSpeedMode('attack', 0)
    traci.vehicle.setLaneChangeMode('attack', 0)

def ego_brake_and_lanechange():
    traci.vehicle.changeLaneRelative('attack', 1, 100)
    traci.vehicle.setSpeedMode('attack', -1)
    traci.vehicle.setLaneChangeMode('attack', -1)
    traci.vehicle.setSpeed('attack', -1)  # -1 to let SUMO control the speed

# Simulation loop
while traci.simulation.getTime() <= 7200:
    traci.simulationStep()

    if var == 'brake':
        ego_brake()
    elif var == 'lanechange':
        ego_lanechange()
    elif var == 'acceleration':
        ego_acceleration()
    elif var == 'base':
        base()        

    if 'ego' in traci.vehicle.getIDList():
        ego_speed = traci.vehicle.getSpeed('ego')
        ego_speeds.append(ego_speed * 3.6)
        times.append(step)

        step += 1
        

traci.close()

# Plot
plt.figure(figsize=(10, 5))
plt.plot(times, ego_speeds, label='ego Speed (km/h)')
plt.xlabel('Time (simulation steps)')
plt.ylabel('Speed (km/h)')
plt.title('Speed of ego Vehicle')
plt.legend()

plt.tight_layout()
plt.show()