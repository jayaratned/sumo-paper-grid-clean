# import pandas as pd
# import matplotlib.pyplot as plt

# csv_file_path = 'outputs.csv'
# chunksize = 10 ** 5  # Adjust this value based on your system's memory capacity and the size of your CSV
# collision_vehicles_mapping = {
#     'ego': 'attacked vehicle',
#     'flow1.1804': 'veh1',
#     'flow1.1808': 'veh2',
#     'flow1.1811': 'veh3',
#     'flow1.1814': 'veh4',
#     'flow1.1817': 'veh5',
#     'flow1.1819': 'veh6',
# }
# collision_vehicles = list(collision_vehicles_mapping.keys())

# # Initialize an empty DataFrame to hold filtered data
# filtered_chunks = []

# for chunk in pd.read_csv(csv_file_path, sep=';', chunksize=chunksize):
#     filtered_columns_chunk = chunk[['data_timestep', 'vehicle_id', 'vehicle_speed', 'vehicle_waiting']]
#     filtered_chunk = filtered_columns_chunk[(filtered_columns_chunk['data_timestep'] >= 2435) & (filtered_columns_chunk['data_timestep'] <= 2460)]
#     final_filtered_chunk = filtered_chunk[filtered_chunk['vehicle_id'].isin(collision_vehicles)]
#     filtered_chunks.append(final_filtered_chunk)

# # Concatenate all the filtered chunks into a single DataFrame
# final_filtered_df = pd.concat(filtered_chunks)

# # Convert vehicle_speed from m/s to km/h
# final_filtered_df['vehicle_speed_kmh'] = final_filtered_df['vehicle_speed'] * 3.6

# # Ensure that 'data_timestep' is sorted to make the plot lines continuous and correct
# final_filtered_df = final_filtered_df.sort_values(by='data_timestep')

# # Set up the plot
# plt.figure(figsize=(10, 6))

# # Loop through each vehicle in collision_vehicles and plot its speed vs timestep with updated labels
# for vehicle_id, label in collision_vehicles_mapping.items():
#     vehicle_data = final_filtered_df[final_filtered_df['vehicle_id'] == vehicle_id]
#     plt.plot(vehicle_data['data_timestep'], vehicle_data['vehicle_speed_kmh'], label=label)

# # Adding plot title and labels
# # plt.title('Speed vs. Timestep for Collision Vehicles')
# plt.xlabel('Timestep (s)')
# plt.ylabel('Speed (km/h)')
# plt.ylim(0, 130)
# plt.xlim(2435, 2460)

# # Show legend
# plt.legend()

# # Show grid
# plt.grid(True)

# # plot tight layout
# plt.tight_layout()

# # save the plot
# plt.savefig('collspeedskmph.pdf', format='pdf', bbox_inches='tight')

# # Show the plot
# plt.show()

import pandas as pd
import matplotlib.pyplot as plt

# File path and configurations
csv_file_path = 'outputs.csv'
chunksize = 10 ** 5
collision_vehicles_mapping = {
    'ego': 'attacked vehicle',
    'flow1.1804': 'vehicle-1',
    'flow1.1808': 'vehicle-2',
    'flow1.1811': 'vehicle-3',
    'flow1.1814': 'vehicle-4',
    'flow1.1817': 'vehicle-5',
    'flow1.1819': 'vehicle-6',
}
collision_vehicles = list(collision_vehicles_mapping.keys())

# Increase overall font size
plt.rcParams.update({'font.size': 14})

# Load and filter the data
filtered_chunks = []
for chunk in pd.read_csv(csv_file_path, sep=';', chunksize=chunksize):
    filtered_columns_chunk = chunk[['data_timestep', 'vehicle_id', 'vehicle_speed', 'vehicle_waiting']]
    filtered_chunk = filtered_columns_chunk[(filtered_columns_chunk['data_timestep'] >= 2435) & (filtered_columns_chunk['data_timestep'] <= 2460)]
    final_filtered_chunk = filtered_chunk[filtered_chunk['vehicle_id'].isin(collision_vehicles)]
    filtered_chunks.append(final_filtered_chunk)

# Concatenate all the filtered chunks into a single DataFrame
final_filtered_df = pd.concat(filtered_chunks)

# Convert vehicle_speed from m/s to km/h
final_filtered_df['vehicle_speed_kmh'] = final_filtered_df['vehicle_speed'] * 3.6

# Ensure 'data_timestep' is sorted
final_filtered_df = final_filtered_df.sort_values(by='data_timestep')

# Set up the plot
plt.figure(figsize=(12, 8))

# Plot each vehicle's data with different styles
for vehicle_id, label in collision_vehicles_mapping.items():
    vehicle_data = final_filtered_df[final_filtered_df['vehicle_id'] == vehicle_id]
    line_style = '-' if vehicle_id != 'ego' else '--'  # Dashed line for the ego vehicle
    line_width = 2.5 if vehicle_id == 'ego' else 1.5  # Thicker line for ego vehicle
    marker = 'o' if vehicle_id == 'ego' else 's'  # Circle markers for ego, square for others
    plt.plot(
        vehicle_data['data_timestep'], 
        vehicle_data['vehicle_speed_kmh'], 
        label=label, 
        linewidth=line_width, 
        # marker=marker,
        markersize=6,
        linestyle=line_style
    )

# Customize the plot
plt.xlabel('Timestep (s)')
plt.ylabel('Speed (km/h)')
plt.ylim(0, 130)
plt.xlim(2435, 2460)
plt.grid(True)
plt.legend()
plt.tight_layout()

# Save the plot
plt.savefig('collspeedskmph.pdf', format='pdf', bbox_inches='tight')

# Show the plot
plt.show()
