import os
import traci
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import csv
import pandas as pd

from .vehicle_utils import get_edges_near_stopped_egos

# Global lists to store data for the entire network
steps_all = []
num_vehicles_all = []
average_speeds_all = []

# Global lists to store data for the vehicles within the radius
steps_in_radius = []
num_vehicles_in_radius = []
average_speeds_in_radius = []

# def collect_simulation_data(radius, warmup_time, baseline=False):
#     """
#     Observer function that collects data at every simulation step starting after
#     warm up till end of simulation.
#     """
#     step = traci.simulation.getTime()
    
#     # Skip data collection during warmup time
#     if step < warmup_time:
#         return

#     vehicle_ids = traci.vehicle.getIDList()

#     # Data for all vehicles
#     speeds_all = [traci.vehicle.getSpeed(veh_id) * 3.6 for veh_id in vehicle_ids]  # converted to km/h
#     steps_all.append(step)
#     num_vehicles_all.append(len(vehicle_ids))
#     average_speeds_all.append(np.mean(speeds_all) if speeds_all else 0)
    
#     # Data for vehicles on selected edges
#     if baseline:
#         # Read edges from .txt file
#         with open('data/outputs/edges_near_stopped_egos.txt', 'r') as file:
#             edges_of_interest = [line.strip().split(":")[1] for line in file]
#     else:
#         edges_of_interest = get_edges_near_stopped_egos(radius)
        
#     vehicle_ids_on_edges = [veh_id for veh_id in vehicle_ids if traci.vehicle.getRoadID(veh_id) in edges_of_interest]
#     speeds_selected = [traci.vehicle.getSpeed(veh_id) * 3.6 for veh_id in vehicle_ids_on_edges]  # converted to km/h
#     steps_in_radius.append(step)
#     num_vehicles_in_radius.append(len(vehicle_ids_on_edges))
#     average_speeds_in_radius.append(np.mean(speeds_selected) if speeds_selected else 0)

#     def save_to_csv(filename, field_suffix, steps, num_vehicles, average_speeds):
#         with open(filename, 'w', newline='') as csvfile:
#             fieldnames = ['Step', f'Num_Vehicles_{field_suffix}', f'Average_Speed_{field_suffix}']
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#             writer.writeheader()
#             for step, num_vehicle, avg_speed in zip(steps, num_vehicles, average_speeds):
#                 writer.writerow({
#                     'Step': step,
#                     f'Num_Vehicles_{field_suffix}': num_vehicle,
#                     f'Average_Speed_{field_suffix}': avg_speed
#                 })

#     # Determine the appropriate suffix and filenames based on 'baseline'
#     suffix = 'attack' if not baseline else 'base'
#     all_vehicles_filename = f'data/outputs/all_vehicles_data_{suffix}.csv'
#     selected_vehicles_filename = f'data/outputs/selected_vehicles_data_{suffix}.csv'

#     # Save the data to CSV files
#     save_to_csv(all_vehicles_filename, suffix, steps_all, num_vehicles_all, average_speeds_all)
#     save_to_csv(selected_vehicles_filename, suffix, steps_in_radius, num_vehicles_in_radius, average_speeds_in_radius)

def plot_collected_data(warmup_time, ego_stop_duration, end_time, data_type="all", interval=300, smoothing=False, baseline=False):
    """
    Process and visualize the collected simulation data.
    
    Parameters:
    - data_type: Either "all" for the entire network or "selected" for selected edges.
    """

    ego_stop_end = warmup_time + ego_stop_duration

    if data_type == "all":
        steps_to_use = steps_all
        num_vehicles_to_use = num_vehicles_all
        average_speeds_to_use = average_speeds_all
    elif data_type == "selected":
        steps_to_use = steps_in_radius
        num_vehicles_to_use = num_vehicles_in_radius
        average_speeds_to_use = average_speeds_in_radius
    else:
        raise ValueError("data_type should be either 'all' or 'selected'")
    
    # Filter the collected data for the given time interval
    filtered_indices = [i for i, t in enumerate(steps_to_use) if warmup_time <= t <= end_time]
    steps_filtered = [steps_to_use[i] for i in filtered_indices]
    num_vehicles_filtered = [num_vehicles_to_use[i] for i in filtered_indices]
    average_speeds_filtered = [average_speeds_to_use[i] for i in filtered_indices]

    # Group the filtered data in intervals and calculate the mean
    average_speeds_interval = [np.mean(average_speeds_filtered[i:i + interval]) for i in range(0, len(average_speeds_filtered), interval)]
    num_vehicles_interval = [np.mean(num_vehicles_filtered[i:i + interval]) for i in range(0, len(num_vehicles_filtered), interval)]

    # Write the data to a csv file
    with open('data/outputs/sumo_data.csv', 'w', newline='') as csvfile:
        fieldnames = [f'{interval}-sec Interval', 'Average_Speed', 'Average_Num_Vehicles']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(len(average_speeds_interval)):
            writer.writerow({f'{interval}-sec Interval': i, 'Average_Speed': average_speeds_interval[i], 'Average_Num_Vehicles': num_vehicles_interval[i]})

        window_size = 5  # Adjust this for more or less smoothing
    
    num_vehicles_series = pd.Series(num_vehicles_interval)
    average_speeds_series = pd.Series(average_speeds_interval)
    
    if smoothing:
        num_vehicles_data = num_vehicles_series.rolling(window=window_size).mean()
        average_speeds_data = average_speeds_series.rolling(window=window_size).mean()
    else:
        num_vehicles_data = num_vehicles_series
        average_speeds_data = average_speeds_series

    # Seaborn settings
    sns.set_style("white")

    # Plotting the data
    plt.figure(figsize=(12,6))

    # First plot with blue color for number of vehicles
    blue_color = "tab:blue"
    ax1 = sns.lineplot(x=steps_filtered[::interval], y=num_vehicles_data, color=blue_color, label="Number of Vehicles")
    ax1.set_xlabel(f'Simulation Step ({interval} s interval from {warmup_time}s to {end_time}s)')
    ax1.set_ylabel('Number of Vehicles', color=blue_color)
    
    # Change the axis marker labels for ax1
    ax1.tick_params(axis='y', colors=blue_color)
    
    # Dashed line for overall average of vehicles
    avg_num_vehicles = np.mean(num_vehicles_data)
    ax1.axhline(avg_num_vehicles, color=blue_color, linestyle='--', label=f'Avg Vehicles: {avg_num_vehicles:.2f}')

    # Second plot with red color for average speeds
    red_color = "tab:red"
    ax2 = plt.twinx()
    sns.lineplot(x=steps_filtered[::interval], y=average_speeds_data, color=red_color, ax=ax2, label="Average Speed (km/h)")
    ax2.set_ylabel('Average Speed (km/h)', color=red_color)
       
    # Change the axis marker labels for ax2
    ax2.tick_params(axis='y', colors=red_color)
    
    # Dashed line for overall average speed
    avg_speed = np.mean(average_speeds_data)
    ax2.axhline(avg_speed, color=red_color, linestyle='--', label=f'Avg Speed: {avg_speed:.2f}')

    # Add vertical lines to mark start_time and end_time
    plt.axvline(x=warmup_time, color='b', linestyle='--', label=f'Start Time: {warmup_time}s')
    plt.axvline(x=ego_stop_end, color='b', linestyle='--', label=f'End Time: {ego_stop_end}s')
    
    # Adjust y-axis range for average speed
    min_speed = min(average_speeds_data.dropna())  # dropna() because rolling can introduce NaN values
    max_speed = max(average_speeds_data.dropna())
    # ax2.set_ylim(min_speed - 5, max_speed + 5)
    ax2.set_ylim(0, 55) # Fixed y-axis range 0 to 55 km/h (speed limit + 5 km/h)

    if data_type == "all":
        plt.title('Network Plot')
    else:
        plt.title('Selected Edges Plot')

    # Save plots to file
    if baseline:
        filename = f"{data_type}_plot_{warmup_time}_to_{end_time}_baseline.png"
    else:
        filename = f"{data_type}_plot_{warmup_time}_to_{end_time}_attack.png"
    # filename = f"{data_type}_plot_{warmup_time}_to_{end_time}.png"
    output_dir = "data/outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    full_path = os.path.join(output_dir, filename)
    plt.savefig(full_path)

    # Debug info
    print(f"Length of steps_to_use: {len(steps_to_use)}")
    print(f"Length of num_vehicles_to_use: {len(num_vehicles_to_use)}")
    print(f"Length of average_speeds_to_use: {len(average_speeds_to_use)}")
    print(f"Sample steps_to_use: {steps_to_use[:5]}")
    print(f"Sample num_vehicles_to_use: {num_vehicles_to_use[:5]}")
    print(f"Sample average_speeds_to_use: {average_speeds_to_use[:5]}")
    print(f"Length of filtered steps: {len(steps_filtered)}")
    print(f"Length of filtered average speeds: {len(average_speeds_filtered)}")
    print(f"Length of filtered num vehicles: {len(num_vehicles_filtered)}")

    # Show the plot
    plt.show()

def comparison_plots(grouping_interval):
    # Function to generate and save plots for each data set
    def generate_plot(df_base_path, df_attack_path, title_prefix):
        df_base = pd.read_csv(df_base_path)
        df_attack = pd.read_csv(df_attack_path)
        
        merged_df = pd.merge(df_base, df_attack, on='Step')
        merged_df['Step_Interval'] = (merged_df['Step'] // grouping_interval) * grouping_interval
        grouped_df = merged_df.groupby('Step_Interval').agg(np.mean).reset_index()
        
        for y_column_prefix in ['Num_Vehicles', 'Average_Speed']:
            plt.figure(figsize=(10, 6))
            sns.lineplot(x='Step_Interval', y=f'{y_column_prefix}_base', data=grouped_df, label=f'{y_column_prefix}_base')
            sns.lineplot(x='Step_Interval', y=f'{y_column_prefix}_attack', data=grouped_df, label=f'{y_column_prefix}_attack')
            plt.xlabel(f'Step Interval ({grouping_interval}-step)')
            plt.ylabel(f'Average {y_column_prefix.replace("_", " ")}')
            title = f'Average {y_column_prefix.replace("_", " ")} vs {grouping_interval}-Step Interval ({title_prefix})'
            plt.title(title)
            plt.legend()
            plt.savefig(f'data/outputs/{title}.png')  # Save the plot
            plt.show()
    
    # Generate and save plots for 'all vehicles' data set
    generate_plot('data/outputs/all_vehicles_data_base.csv', 'data/outputs/all_vehicles_data_attack.csv', 'All Vehicles')
    
    # Generate and save plots for 'selected vehicles' data set
    generate_plot('data/outputs/selected_vehicles_data_base.csv', 'data/outputs/selected_vehicles_data_attack.csv', 'Selected Vehicles')

# def comparison_plots(grouping_interval):
    # Read data from CSV files ALL VEHICLES
    df_base = pd.read_csv('data/outputs/all_vehicles_data_base.csv')  # Replace with the actual path to your base CSV file
    df_attack = pd.read_csv('data/outputs/all_vehicles_data_attack.csv')  # Replace with the actual path to your attack CSV file

    # Merge both dataframes based on the 'Step' column
    merged_df = pd.merge(df_base, df_attack, on='Step')

    # Define step interval for averaging
    step_interval = grouping_interval

    # Create a new column to specify which interval each step belongs to
    merged_df['Step_Interval'] = (merged_df['Step'] // step_interval) * step_interval

    # Group by Step_Interval and average the other columns
    grouped_df = merged_df.groupby('Step_Interval').agg(np.mean).reset_index()

    # Plot Number of Vehicles vs Step Interval
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='Step_Interval', y='Num_Vehicles_base', data=grouped_df, label='Num_Vehicles_base')
    sns.lineplot(x='Step_Interval', y='Num_Vehicles_attack', data=grouped_df, label='Num_Vehicles_attack')
    plt.xlabel(f'Step Interval ({step_interval}-step)')
    plt.ylabel('Average Number of Vehicles')
    plt.title(f'Average Number of Vehicles vs {step_interval}-Step Interval')
    plt.legend()
    plt.show()

    # Plot Average Speed vs Step Interval
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='Step_Interval', y='Average_Speed_base', data=grouped_df, label='Average_Speed_base')
    sns.lineplot(x='Step_Interval', y='Average_Speed_attack', data=grouped_df, label='Average_Speed_attack')
    plt.xlabel(f'Step Interval ({step_interval}-step)')
    plt.ylabel('Average Speed (km/h)')
    plt.title(f'Average Speed vs {step_interval}-Step Interval')
    plt.legend()
    plt.show()

    # Read data from CSV files SELECTED VEHICLES
    df_base = pd.read_csv('data/outputs/selected_vehicles_data_base.csv')  # Replace with the actual path to your base CSV file
    df_attack = pd.read_csv('data/outputs/selected_vehicles_data_attack.csv')  # Replace with the actual path to your attack CSV file

    # Merge both dataframes based on the 'Step' column
    merged_df = pd.merge(df_base, df_attack, on='Step')

    # Define step interval for averaging
    step_interval = grouping_interval

    # Create a new column to specify which interval each step belongs to
    merged_df['Step_Interval'] = (merged_df['Step'] // step_interval) * step_interval

    # Group by Step_Interval and average the other columns
    grouped_df = merged_df.groupby('Step_Interval').agg(np.mean).reset_index()

    # Plot Number of Vehicles vs Step Interval
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='Step_Interval', y='Num_Vehicles_base', data=grouped_df, label='Num_Vehicles_base')
    sns.lineplot(x='Step_Interval', y='Num_Vehicles_attack', data=grouped_df, label='Num_Vehicles_attack')
    plt.xlabel(f'Step Interval ({step_interval}-step)')
    plt.ylabel('Average Number of Vehicles')
    plt.title(f'Average Number of Vehicles vs {step_interval}-Step Interval')
    plt.legend()
    plt.show()

    # Plot Average Speed vs Step Interval
    plt.figure(figsize=(10, 6))
    sns.lineplot(x='Step_Interval', y='Average_Speed_base', data=grouped_df, label='Average_Speed_base')
    sns.lineplot(x='Step_Interval', y='Average_Speed_attack', data=grouped_df, label='Average_Speed_attack')
    plt.xlabel(f'Step Interval ({step_interval}-step)')
    plt.ylabel('Average Speed (km/h)')
    plt.title(f'Average Speed vs {step_interval}-Step Interval')
    plt.legend()
    plt.show()