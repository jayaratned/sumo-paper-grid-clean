import pandas as pd

csv_file_path = 'outputs.csv'
df = pd.read_csv(csv_file_path, sep=';')

filtered_columns_df = df[['data_timestep', 'vehicle_id', 'vehicle_speed', 'vehicle_waiting']]
filtered_df = filtered_columns_df[(filtered_columns_df['data_timestep'] >= 440) & (filtered_columns_df['data_timestep'] <= 460)]

collision_vehicles = ['ego', 'flow1.303', 'flow1.301', 'flow1.304', 'flow1.307', 'flow1.304', 'flow1.306']

final_filtered_df = filtered_df[filtered_df['vehicle_id'].isin(collision_vehicles)]

print(final_filtered_df.head())

import matplotlib.pyplot as plt

# Convert vehicle_speed from m/s to mph
final_filtered_df['vehicle_speed_mph'] = final_filtered_df['vehicle_speed'] * 2.23694

# Ensure that 'data_timestep' is sorted to make the plot lines continuous and correct
final_filtered_df = final_filtered_df.sort_values(by='data_timestep')

# Set up the plot
plt.figure(figsize=(10, 6))

# Loop through each vehicle in collision_vehicles and plot its speed vs timestep
for vehicle_id in collision_vehicles:
    # Filter the DataFrame for the current vehicle
    vehicle_data = final_filtered_df[final_filtered_df['vehicle_id'] == vehicle_id]
    
    # Plot speed vs timestep
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
