# import pandas as pd

# csv_file_path = 'outputs.csv'
# df = pd.read_csv(csv_file_path, sep=';')

# filtered_columns_df = df[['data_timestep', 'vehicle_id', 'vehicle_speed', 'vehicle_waiting']]
# filtered_df = filtered_columns_df[(filtered_columns_df['data_timestep'] >= 2435) & (filtered_columns_df['data_timestep'] <= 2455)]

# collision_vehicles = ['ego', 'flow1.1804', 'flow1.1808', 'flow1.1811', 'flow1.1814', 'flow1.1817', 'flow1.1819']

# final_filtered_df = filtered_df[filtered_df['vehicle_id'].isin(collision_vehicles)]

# print(final_filtered_df.head())

# import matplotlib.pyplot as plt

# # Convert vehicle_speed from m/s to mph
# final_filtered_df['vehicle_speed_mph'] = final_filtered_df['vehicle_speed'] * 2.23694

# # Ensure that 'data_timestep' is sorted to make the plot lines continuous and correct
# final_filtered_df = final_filtered_df.sort_values(by='data_timestep')

# # Set up the plot
# plt.figure(figsize=(10, 6))

# # Loop through each vehicle in collision_vehicles and plot its speed vs timestep
# for vehicle_id in collision_vehicles:
#     # Filter the DataFrame for the current vehicle
#     vehicle_data = final_filtered_df[final_filtered_df['vehicle_id'] == vehicle_id]
    
#     # Plot speed vs timestep
#     plt.plot(vehicle_data['data_timestep'], vehicle_data['vehicle_speed_mph'], label=vehicle_id)

# # Adding plot title and labels
# plt.title('Speed vs. Timestep for Collision Vehicles')
# plt.xlabel('Timestep')
# plt.ylabel('Speed (mph)')
# plt.ylim(-1, 80)

# # Show legend
# plt.legend()

# # Show grid
# plt.grid(True)

# # Show the plot
# plt.show()

import pandas as pd
import matplotlib.pyplot as plt

csv_file_path = 'outputs.csv'
chunksize = 10 ** 5  # Adjust this value based on your system's memory capacity and the size of your CSV
collision_vehicles = ['ego', 'flow1.1804', 'flow1.1808', 'flow1.1811', 'flow1.1814', 'flow1.1817', 'flow1.1819']

# Initialize an empty DataFrame to hold filtered data
filtered_chunks = []

for chunk in pd.read_csv(csv_file_path, sep=';', chunksize=chunksize):
    filtered_columns_chunk = chunk[['data_timestep', 'vehicle_id', 'vehicle_speed', 'vehicle_waiting']]
    filtered_chunk = filtered_columns_chunk[(filtered_columns_chunk['data_timestep'] >= 2435) & (filtered_columns_chunk['data_timestep'] <= 2460)]
    final_filtered_chunk = filtered_chunk[filtered_chunk['vehicle_id'].isin(collision_vehicles)]
    filtered_chunks.append(final_filtered_chunk)

# Concatenate all the filtered chunks into a single DataFrame
final_filtered_df = pd.concat(filtered_chunks)

# Convert vehicle_speed from m/s to mph
final_filtered_df['vehicle_speed_mph'] = final_filtered_df['vehicle_speed'] * 2.23694

# Ensure that 'data_timestep' is sorted to make the plot lines continuous and correct
final_filtered_df = final_filtered_df.sort_values(by='data_timestep')

# Set up the plot
plt.figure(figsize=(10, 6))

# Loop through each vehicle in collision_vehicles and plot its speed vs timestep
for vehicle_id in collision_vehicles:
    vehicle_data = final_filtered_df[final_filtered_df['vehicle_id'] == vehicle_id]
    plt.plot(vehicle_data['data_timestep'], vehicle_data['vehicle_speed_mph'], label=vehicle_id)

# Adding plot title and labels
plt.title('Speed vs. Timestep for Collision Vehicles')
plt.xlabel('Timestep')
plt.ylabel('Speed (mph)')
plt.ylim(-1, 80)

# Show legend
plt.legend()

# Show grid
plt.grid(True)

# Show the plot
plt.show()

