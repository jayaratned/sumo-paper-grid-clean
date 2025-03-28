import traci
import matplotlib.pyplot as plt

# Start TraCI
traci.start(["sumo-gui", "-c", "safety.sumocfg"])

normal_speeds = []
attack_speeds = []
normal_positions = []
attack_positions = []
times = []
step = 0

# Simulation loop
while traci.simulation.getTime() <= 120:
    traci.simulationStep()

    # Collect speeds and time
    if 'normal' in traci.vehicle.getIDList():
        normal_speed = traci.vehicle.getSpeed('normal')
        normal_speeds.append(normal_speed * 3.6)
        normal_position = traci.vehicle.getLanePosition('normal')
        normal_positions.append(normal_position)
    else:
        normal_speeds.append(None)
        normal_positions.append(None)

    if 'attack' in traci.vehicle.getIDList():
        # Disable safety checks for the 'attack'
        traci.vehicle.setSpeedMode('attack', 0)
        traci.vehicle.setLaneChangeMode('attack', 0)
        if traci.simulation.getTime() == 90:
            print('Changing lane')
            traci.vehicle.changeLaneRelative('attack', 1, 100)
            # traci.vehicle.setSpeed('attack', 13.89)

        attack_speed = traci.vehicle.getSpeed('attack')
        attack_speeds.append(attack_speed * 3.6)

        attack_position = traci.vehicle.getLanePosition('attack')
        attack_positions.append(attack_position)
        distance = normal_position - attack_position

        colliding_vehicles = traci.simulation.getCollidingVehiclesIDList()
        if colliding_vehicles:
            print('Collision!')
            traci.vehicle.setSpeedMode('attack', -1)
            traci.vehicle.setLaneChangeMode('attack', -1)
            traci.vehicle.setSpeed('attack', -1)  # -1 to let SUMO control the speed

    else:
        attack_speeds.append(None)
        attack_positions.append(None)

    times.append(step)
    step += 1

traci.close()


# save the data to csv file
import csv
with open('speeds.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['time', 'normal_speed', 'normal_position', 'attack_speed', 'attack_position'])
    for i in range(len(times)):
        writer.writerow([times[i], normal_speeds[i], normal_positions[i], attack_speeds[i], attack_positions[i]])

# Plotting
fig, axs = plt.subplots(2, 1, figsize=(10, 10))  # Two subplots

# Speed plot
axs[0].plot(times, normal_speeds, label='normal Speed (km/h)')
axs[0].plot(times, attack_speeds, label='attack Speed (km/h)')
axs[0].set_xlabel('Time (simulation steps)')
axs[0].set_ylabel('Speed (km/h)')
axs[0].set_title('Speeds of normal and attack Vehicles')
axs[0].legend()
axs[0].set_ylim(0, 60)
axs[0].set_xlim(0, )

# Distance plot
axs[1].plot(times, normal_positions, label='normal Distance (m)', linestyle='--')
axs[1].plot(times, attack_positions, label='attack Distance (m)', linestyle='--')
axs[1].set_xlabel('Time (simulation steps)')
axs[1].set_ylabel('Distance (m)')
axs[1].set_title('Distances of normal and attack Vehicles')
axs[1].legend()
axs[1].set_ylim(0, )
axs[1].set_xlim(0, )

plt.tight_layout()
plt.show()
