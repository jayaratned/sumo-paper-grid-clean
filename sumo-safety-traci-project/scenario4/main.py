import traci
import matplotlib.pyplot as plt

# Start TraCI
traci.start(["sumo-gui", "-c", "safety.sumocfg"])

leader_speeds = []
follower_speeds = []
leader_positions = []
follower_positions = []
times = []
step = 0

# Simulation loop
while traci.simulation.getTime() <= 60:
    traci.simulationStep()

    # Collect speeds and time
    if 'leader' in traci.vehicle.getIDList():
        leader_speed = traci.vehicle.getSpeed('leader')
        leader_speeds.append(leader_speed * 3.6)
        leader_position = traci.vehicle.getLanePosition('leader')
        leader_positions.append(leader_position)
    else:
        leader_speeds.append(None)
        leader_positions.append(None)

    if 'follower' in traci.vehicle.getIDList():
        follower_speed = traci.vehicle.getSpeed('follower')
        follower_speeds.append(follower_speed * 3.6)

        follower_position = traci.vehicle.getLanePosition('follower')
        follower_positions.append(follower_position)
        distance = leader_position - follower_position

        # If the distance is greater than a certain threshold, keep controlling the speed
        if distance > 10:  # for example, 10 meters
            # Disable safety checks for the 'follower'
            traci.vehicle.setSpeedMode('follower', 0)
            traci.vehicle.setLaneChangeMode('follower', 0)
            traci.vehicle.setSpeed('follower', 13.89)
        else:
            # Once close enough, stop overriding the speed to allow natural behavior
            traci.vehicle.setSpeedMode('follower', -1)
            traci.vehicle.setLaneChangeMode('follower', -1)
            traci.vehicle.setSpeed('follower', -1)  # -1 to let SUMO control the speed

    else:
        follower_speeds.append(None)
        follower_positions.append(None)

    times.append(step)
    step += 0.001

traci.close()


# save the data to csv file
import csv
with open('speeds.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['time', 'leader_speed', 'leader_position', 'follower_speed', 'follower_position'])
    for i in range(len(times)):
        writer.writerow([times[i], leader_speeds[i], leader_positions[i], follower_speeds[i], follower_positions[i]])

# Plotting
fig, axs = plt.subplots(2, 1, figsize=(10, 10))  # Two subplots

# Speed plot
axs[0].plot(times, leader_speeds, label='Leader Speed (km/h)')
axs[0].plot(times, follower_speeds, label='Follower Speed (km/h)')
axs[0].set_xlabel('Time (simulation steps)')
axs[0].set_ylabel('Speed (km/h)')
axs[0].set_title('Speeds of Leader and Follower Vehicles')
axs[0].legend()
# axs[0].set_ylim(0, 60)
axs[0].set_xlim(0, 60)

# Distance plot
axs[1].plot(times, leader_positions, label='Leader Distance (m)', linestyle='--')
axs[1].plot(times, follower_positions, label='Follower Distance (m)', linestyle='--')
axs[1].set_xlabel('Time (simulation steps)')
axs[1].set_ylabel('Distance (m)')
axs[1].set_title('Distances of Leader and Follower Vehicles')
axs[1].legend()
axs[1].set_ylim(0, )
axs[1].set_xlim(0, )

plt.tight_layout()
plt.show()

