# since running on virtual env with sumo installed on it, we don't need to set the path

import traci
import matplotlib.pyplot as plt

# Start TraCI
traci.start(["sumo-gui", "-c", "safety.sumocfg"])

leader_speeds = []
follower_speeds = []
leader_distances = [None]  # Initialize with 0 to represent the start of simulation
follower_distances = [None]  # Initialize with 0 to represent the start of simulation
times = []
step = 0

# Simulation loop
while traci.simulation.getTime() <= 60:
    traci.simulationStep()

    if 'follower' in traci.vehicle.getIDList():
            # Disable safety checks for the 'follower1'
            traci.vehicle.setSpeedMode('follower', 0)
            traci.vehicle.setLaneChangeMode('follower', 0)

            # Set speed of follower to 50kmph
            traci.vehicle.setSpeed('follower', 13.89)


    # Collect speeds and time
    if 'leader' in traci.vehicle.getIDList():
        leader_speed = traci.vehicle.getSpeed('leader')
        leader_speeds.append(leader_speed * 3.6)
        # Calculate the distance traveled since the last step and add to the total
        if leader_distances[-1] is not None:
            leader_distances.append(leader_distances[-1] + leader_speed * traci.simulation.getDeltaT())
        else:
            leader_distances.append(leader_speed * traci.simulation.getDeltaT())
    else:
        leader_speeds.append(None)
        leader_distances.append(None) # Keep the last known distance

    if 'follower' in traci.vehicle.getIDList():
        follower_speed = traci.vehicle.getSpeed('follower')
        follower_speeds.append(follower_speed * 3.6)
        # Calculate the distance traveled since the last step and add to the total
        if follower_distances[-1] is not None:
            follower_distances.append(follower_distances[-1] + follower_speed * traci.simulation.getDeltaT())
        else:
            follower_distances.append(follower_speed * traci.simulation.getDeltaT())
    else:
        follower_speeds.append(None)
        follower_distances.append(None) # Keep the last known distance

    times.append(step)
    step += 0.001

traci.close()

# delete the first element of the distance lists (0) to make them the same size as the speed list
del leader_distances[0]
del follower_distances[0]

# save the data to csv file
import csv
with open('speeds.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['time', 'leader_speed', 'leader_distances', 'follower_speed', 'follower_distances'])
    for i in range(len(times)):
        writer.writerow([times[i], leader_speeds[i], leader_distances[i], follower_speeds[i], follower_distances[i]])

# Plotting
fig, axs = plt.subplots(2, 1, figsize=(10, 10))  # Two subplots

# Speed plot
axs[0].plot(times, leader_speeds, label='Leader Speed (km/h)')
axs[0].plot(times, follower_speeds, label='Follower Speed (km/h)')
axs[0].set_xlabel('Time (simulation steps)')
axs[0].set_ylabel('Speed (km/h)')
axs[0].set_title('Speeds of Leader and Follower Vehicles')
axs[0].legend()
axs[0].set_ylim(0, 60)
axs[0].set_xlim(0, 60)

# Distance plot
axs[1].plot(times, leader_distances, label='Leader Distance (km)', linestyle='--')
axs[1].plot(times, follower_distances, label='Follower Distance (km)', linestyle='--')
axs[1].set_xlabel('Time (simulation steps)')
axs[1].set_ylabel('Distance (km)')
axs[1].set_title('Distances of Leader and Follower Vehicles')
axs[1].legend()
axs[1].set_ylim(0, )
axs[1].set_xlim(0, 60)

plt.tight_layout()
plt.show()
