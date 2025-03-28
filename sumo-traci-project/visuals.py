import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('Qt5Agg')  # or 'Qt5Agg', etc., depending on what you have installed
import matplotlib.pyplot as plt
import configparser
import subprocess
import os
import csv
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from scipy.signal import savgol_filter  

# Read settings from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

PROJECT = config['Files']['Project']
NET_FILE_PATH = config['Files']['Net_File_Path']
SCENARIO = config['Simulation']['Scenario']
WARMUP_TIME = int(config['Simulation']['Warmup_Time'])
BREAKDOWN_TIME = int(config['Simulation']['ego_Breakdown_Time'])
BREAKDOWN_DURATION = int(config['Simulation']['ego_Breakdown_Duration'])
SIMULATION_END_TIME = int(config['Simulation']['End_Time'])
RADIUS_VISUAL = config.getboolean('Visualization', 'radius_visual')
RADIUS = int(config['Simulation']['Radius'])


# new functions


def combine_speeds_and_counts(project, scenario):
    try:
        # File paths
        file_paths = {
            "Attack_speeds": f"data/{project}/outputs/{scenario}/attack_mean_speeds.csv",
            "Base_speeds": f"data/{project}/outputs/{scenario}/base_mean_speeds.csv",
            "Attack_counts": f"data/{project}/outputs/{scenario}/attack_vehicle_counts.csv",
            "Base_counts": f"data/{project}/outputs/{scenario}/base_vehicle_counts.csv"
        }

        # Load the data and rename columns
        data = {}
        for name, path in file_paths.items():
            prefix = name.split('_')[0]  # 'attack' or 'baseline'
            df = pd.read_csv(path)

            # Rename columns to have the prefix, except for 'Step'
            df.rename(columns={col: f"{prefix}_{col}" for col in df.columns if col != 'Step'}, inplace=True)

            # Calculate moving averages
            window_size = 600
            for col in df.columns:
                if 'Mean_Speed' in col or 'Count' in col:
                    df[f'{col}_MA'] = df[col].rolling(window=window_size, min_periods=1).mean() # _size ,min_periods=1 to avoid NaNs at the beginning

            data[name] = df

        # Merge dataframes on 'Step'
        merged_data = None
        for df in data.values():
            if merged_data is None:
                merged_data = df
            else:
                merged_data = pd.merge(merged_data, df, on='Step', how='inner')

        # Save the merged data to a csv file
        save_path = f"data/{project}/outputs/{scenario}/combined_speed_count_data.csv"
        merged_data.to_csv(save_path, index=False)
        print(f"Combined data saved to: {save_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

def mean_speeds_and_counts(project, scenario, warmup_time, simulation_end_time, breakdown_time, breakdown_duration):
    # Load the combined data
    speed_count_data = pd.read_csv(f"data/{project}/outputs/{scenario}/combined_speed_count_data.csv")

    # Calculate the end time of the breakdown
    breakdown_end_time = breakdown_time + breakdown_duration

    # Filter data for the time range of interest
    filtered_data = speed_count_data[(speed_count_data['Step'] >= breakdown_time) & (speed_count_data['Step'] <= breakdown_end_time)]

    # Initialize a dictionary to store mean values
    means = {}

    # Calculate mean speeds and counts for both scenarios and both types ('all' and 'in_radius')
    for scenario_prefix in ['Attack', 'Base']:
        for data_type in ['Mean_Speed_All', 'Mean_Speed_In_Radius', 'Count_All', 'Count_In_Radius']:
            key = f'{scenario_prefix}_{data_type}'
            means[key] = filtered_data[key].mean()

    # Convert the dictionary to a DataFrame for saving
    means_df = pd.DataFrame([means])

    # Save the DataFrame to a CSV file
    save_path = f"data/{project}/outputs/{scenario}/mean_speeds_counts_summary.csv"
    means_df.to_csv(save_path, index=False)
    print(f"Mean speeds and counts saved to: {save_path}")

    # Return or print the calculated means
    return means

def plot_mean_speed_graph(project, scenario, warmup_time, simulation_end_time, breakdown_time, breakdown_duration, threshold_fraction=0.1):
    # File path for combined data
    combined_file_path = f"data/{project}/outputs/{scenario}/combined_speed_count_data.csv"

    # Load the combined data
    combined_data = pd.read_csv(combined_file_path)

    # Apply the Savitzky-Golay filter to the speed columns
    window_length, poly_order = 301, 3  # These need to be chosen based on your dataset
    for col in ['Attack_Mean_Speed_All', 'Attack_Mean_Speed_In_Radius', 'Base_Mean_Speed_All', 'Base_Mean_Speed_In_Radius']:
        combined_data[f'{col}_Smooth'] = savgol_filter(combined_data[col], window_length, poly_order)

    # Plotting using seaborn
    plt.figure(figsize=(12, 6))

    # Mean_Speed_All
    plt.subplot(2, 1, 1)
    sns.lineplot(data=combined_data, x='Step', y='Attack_Mean_Speed_All_Smooth', color='red', label='Attack')
    sns.lineplot(data=combined_data, x='Step', y='Base_Mean_Speed_All_Smooth', color='blue', label='Baseline')
    plt.title(f'Mean Speed All vs Step in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)

    # Highlighting breakdown time and recovery point (if applicable)
    recovery_times = find_and_print_recovery_times(project, scenario, breakdown_time, breakdown_duration, threshold_fraction)
    mark_breakdown_and_recovery(plt, breakdown_time, breakdown_duration, recovery_times.get('Mean_Speed_All'))

    # Mean_Speed_In_Radius
    plt.subplot(2, 1, 2)
    sns.lineplot(data=combined_data, x='Step', y='Attack_Mean_Speed_In_Radius_Smooth', color='red', label='Attack')
    sns.lineplot(data=combined_data, x='Step', y='Base_Mean_Speed_In_Radius_Smooth', color='blue', label='Baseline')
    plt.title(f'Mean Speed In Radius vs Step in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)

    mark_breakdown_and_recovery(plt, breakdown_time, breakdown_duration, recovery_times.get('Mean_Speed_In_Radius'))

    plt.tight_layout()

    # Save the plot
    save_path = f"data/{project}/outputs/{scenario}/mean_speed_comparison_plot.png"
    plt.savefig(save_path)
    plt.show()
    print(f"Plot saved to: {save_path}")

def plot_vehicle_count_graph(project, scenario, warmup_time, simulation_end_time, breakdown_time, breakdown_duration, threshold_fraction=0.1):
    # File path for combined data
    combined_file_path = f"data/{project}/outputs/{scenario}/combined_speed_count_data.csv"

    # Load the combined data
    combined_data = pd.read_csv(combined_file_path)

    # Apply the Savitzky-Golay filter to the speed columns
    window_length, poly_order = 301, 3  # These need to be chosen based on your dataset
    for col in ['Attack_Count_All', 'Attack_Count_In_Radius', 'Base_Count_All', 'Base_Count_In_Radius']:
        combined_data[f'{col}_Smooth'] = savgol_filter(combined_data[col], window_length, poly_order)

    # Plotting using seaborn
    plt.figure(figsize=(12, 6))

    # Count_All
    plt.subplot(2, 1, 1)
    sns.lineplot(data=combined_data, x='Step', y='Attack_Count_All_Smooth', color='red', label='Attack')
    sns.lineplot(data=combined_data, x='Step', y='Base_Count_All_Smooth', color='blue', label='Baseline')
    plt.title(f'Mean Speed All vs Step in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)

    # Highlighting breakdown time and recovery point (if applicable)
    recovery_times = find_and_print_recovery_times(project, scenario, breakdown_time, breakdown_duration, threshold_fraction)
    mark_breakdown_and_recovery(plt, breakdown_time, breakdown_duration, recovery_times.get('Count_All'))

    # Count_In_Radius
    plt.subplot(2, 1, 2)
    sns.lineplot(data=combined_data, x='Step', y='Attack_Count_In_Radius_Smooth', color='red', label='Attack')
    sns.lineplot(data=combined_data, x='Step', y='Base_Count_In_Radius_Smooth', color='blue', label='Baseline')
    plt.title(f'Mean Speed In Radius vs Step in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)

    mark_breakdown_and_recovery(plt, breakdown_time, breakdown_duration, recovery_times.get('Count_In_Radius'))

    plt.tight_layout()

    # Save the plot
    save_path = f"data/{project}/outputs/{scenario}/Count_comparison_plot.png"
    plt.savefig(save_path)
    plt.show()
    print(f"Plot saved to: {save_path}")

def find_and_print_recovery_times(project, scenario, breakdown_time, breakdown_duration, threshold_fraction):
    
    # File path for combined data
    combined_file_path = f"data/{project}/outputs/{scenario}/combined_speed_count_data.csv"

    # Load the combined data
    combined_data = pd.read_csv(combined_file_path)

    # Calculate the end time of the attack
    attack_end_time = breakdown_time + breakdown_duration

    # Initialize dictionary to store recovery times
    recovery_times = {}

    # Combine the data types into a single list
    data_types = ['Mean_Speed_All', 'Mean_Speed_In_Radius', 'Count_All', 'Count_In_Radius']

    # Find recovery time for each scenario
    for data_type in data_types:
        recovery_condition = (combined_data[f'Attack_{data_type}_MA'] >= (1 - threshold_fraction) * combined_data[f'Base_{data_type}_MA']) & (combined_data['Step'] > attack_end_time)
        recovery_times_col = combined_data[recovery_condition]['Step']
        recovery_times[data_type] = recovery_times_col.iloc[0] if not recovery_times_col.empty else None

    # Print the recovery times
    for key, time in recovery_times.items():
        if time is not None:
            print(f"Recovery time for {key}: {time}")
        else:
            print(f"No recovery point found within the threshold for {key} after the attack.")

    return recovery_times

def find_and_print_recovery_times1(project, scenario, breakdown_time, breakdown_duration, threshold_fraction):
    
    # File path for combined data
    combined_file_path = f"data/{project}/outputs/{scenario}/combined_speed_count_data.csv"

    # Load the combined data
    combined_data = pd.read_csv(combined_file_path)

    # Calculate the end time of the attack
    attack_end_time = breakdown_time + breakdown_duration

    # Initialize dictionary to store recovery times
    recovery_times = {}

    # Find recovery time for each scenario ('all' and 'in_radius')
    for data_type in ['Mean_Speed_All', 'Mean_Speed_In_Radius']:
        recovery_condition = (combined_data[f'Attack_{data_type}_MA'] >= (1 - threshold_fraction) * combined_data[f'Base_{data_type}_MA']) & (combined_data['Step'] > attack_end_time)
        recovery_times_col = combined_data[recovery_condition]['Step']

        recovery_times[data_type] = recovery_times_col.iloc[0] if not recovery_times_col.empty else None

    # Find recovery time for each scenario ('all' and 'in_radius')
    for data_type in ['Count_All', 'Count_In_Radius']:
        recovery_condition = (combined_data[f'Attack_{data_type}_MA'] >= (1 - threshold_fraction) * combined_data[f'Base_{data_type}_MA']) & (combined_data['Step'] > attack_end_time)
        recovery_times_col = combined_data[recovery_condition]['Step']

        recovery_times[data_type] = recovery_times_col.iloc[0] if not recovery_times_col.empty else None

    # Print the recovery times
    for key, time in recovery_times.items():
        if time is not None:
            print(f"Recovery time for {key}: {time}")
        else:
            print(f"No recovery point found within the threshold for {key} after the attack.")

    return recovery_times

def mark_breakdown_and_recovery(plt, breakdown_time, breakdown_duration, recovery_time):
    plt.axvline(x=breakdown_time, color='black', linestyle='--', label='Breakdown Start')
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--', label='Breakdown End')
    if recovery_time:
        plt.axvline(x=recovery_time, color='green', linestyle='--', label='Recovery Point')
    ymin, ymax = plt.ylim()
    padding = 0.05
    ymin -= padding
    ymax += padding
    plt.ylim(ymin, ymax)
    plt.fill_betweenx([ymin, ymax], breakdown_time, breakdown_time + breakdown_duration, color='pink', alpha=0.2)
    if recovery_time:
        plt.fill_betweenx([ymin, ymax], breakdown_time + breakdown_duration, recovery_time, color='lightgreen', alpha=0.3, label='Recovery Period')

# previous functions

def plot_mean_speed_graph_old(project, scenario, warmup_time, simulation_end_time, breakdown_time, breakdown_duration, threshold_fraction=0.1):
    # File paths
    attack_file_path = f"data/{project}/outputs/{scenario}/attack_mean_speeds.csv"
    baseline_file_path = f"data/{project}/outputs/{scenario}/base_mean_speeds.csv"

    # Load the data
    attack_data = pd.read_csv(attack_file_path)
    baseline_data = pd.read_csv(baseline_file_path)

    # Calculate moving averages for both datasets
    window_size = 300  # Window size for the moving average
    attack_data['Attack_Mean_Speed_All_MA'] = attack_data['Mean_Speed_All'].rolling(window=window_size).mean()
    baseline_data['Base_Mean_Speed_All_MA'] = baseline_data['Mean_Speed_All'].rolling(window=window_size).mean()

    attack_data['Attack_Mean_Speed_In_Radius_MA'] = attack_data['Mean_Speed_In_Radius'].rolling(window=window_size).mean()
    baseline_data['Base_Mean_Speed_In_Radius_MA'] = baseline_data['Mean_Speed_In_Radius'].rolling(window=window_size).mean()

    # save the moving averages to csv files
    attack_data.to_csv(f"data/{project}/outputs/{scenario}/attack_mean_speeds_MA.csv", index=False)
    baseline_data.to_csv(f"data/{project}/outputs/{scenario}/base_mean_speeds_MA.csv", index=False)

    # Calculate and print the recovery times for both subplots
    recovery_time_all = find_recovery_time(
        attack_data,
        baseline_data,
        'Attack_Mean_Speed_All_MA',
        'Base_Mean_Speed_All_MA',  # add this argument for the baseline data
        threshold_fraction,
        # window_size,
        breakdown_time + breakdown_duration
    )

    recovery_time_in_radius = find_recovery_time(
        attack_data,
        baseline_data,
        'Attack_Mean_Speed_In_Radius_MA',
        'Base_Mean_Speed_In_Radius_MA',  # add this argument for the baseline data
        threshold_fraction,
        # window_size,
        breakdown_time + breakdown_duration
    )

    # Apply the Savitzky-Golay filter to the speed columns
    window_length, poly_order = 301, 3  # These need to be chosen based on your dataset
    attack_data['Mean_Speed_All_Smooth'] = savgol_filter(attack_data['Mean_Speed_All'], window_length, poly_order)
    attack_data['Mean_Speed_In_Radius_Smooth'] = savgol_filter(attack_data['Mean_Speed_In_Radius'], window_length, poly_order)
    baseline_data['Mean_Speed_All_Smooth'] = savgol_filter(baseline_data['Mean_Speed_All'], window_length, poly_order)
    baseline_data['Mean_Speed_In_Radius_Smooth'] = savgol_filter(baseline_data['Mean_Speed_In_Radius'], window_length, poly_order)


    # Add a new column to differentiate the scenarios
    attack_data['Scenario'] = 'Attack'
    baseline_data['Scenario'] = 'Baseline'

    # Combine both dataframes
    combined_data = pd.concat([attack_data, baseline_data])

    # Plotting using seaborn
    plt.figure(figsize=(12, 6))

    # Mean_Speed_All
    plt.subplot(2, 1, 1)
    sns.lineplot(data=combined_data, x='Step', y='Mean_Speed_All_Smooth', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f'Mean Speed All vs Step in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits

    # Highlight the recovery point with a green vertical line if it exists
    if recovery_time_all:
        plt.axvline(x=recovery_time_all, color='green', linestyle='--', label='Recovery Point All')


    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')
    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    if recovery_time_all:
        plt.fill_between(x=[breakdown_time + breakdown_duration, recovery_time_all], y1=ymin, y2=ymax, color='lightgreen', alpha=0.3, label='Recovery Period All')

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)


    # Mean_Speed_In_Radius
    plt.subplot(2, 1, 2)
    sns.lineplot(data=combined_data, x='Step', y='Mean_Speed_In_Radius_Smooth', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f'Mean Speed In Radius vs Step in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # Highlight the recovery point with a green vertical line if it exists
    if recovery_time_in_radius:
        plt.axvline(x=recovery_time_in_radius, color='green', linestyle='--', label='Recovery Point In Radius')


    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    if recovery_time_in_radius:
        plt.fill_between(x=[breakdown_time + breakdown_duration, recovery_time_in_radius], y1=ymin, y2=ymax, color='lightgreen', alpha=0.3, label='Recovery Period In Radius')

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    plt.tight_layout()
    
    # Save the plot
    save_path = f"data/{project}/outputs/{scenario}/mean_speed_comparison_plot.png"
    plt.savefig(save_path)
    plt.show()
    print(f"Plot saved to: {save_path}")

    # Print the recovery times for both subplots
    print_recovery_times(recovery_time_all, recovery_time_in_radius)

def plot_vehicle_count_graph1(project, scenario, warmup_time, simulation_end_time, breakdown_time, breakdown_duration, threshold_fraction=0.1):
    # File paths
    attack_file_path = f"data/{project}/outputs/{scenario}/attack_vehicle_counts.csv"
    baseline_file_path = f"data/{project}/outputs/{scenario}/base_vehicle_counts.csv"

    # Load the data
    attack_data = pd.read_csv(attack_file_path)
    baseline_data = pd.read_csv(baseline_file_path)

    # Add a new column to differentiate the scenarios
    attack_data['Scenario'] = 'Attack'
    baseline_data['Scenario'] = 'Baseline'

    # Calculate moving averages for both datasets
    window_size = 300  # Window size for the moving average
    attack_data['Attack_Count_All_MA'] = attack_data['Count_All'].rolling(window=window_size).mean()
    baseline_data['Base_Count_All_MA'] = baseline_data['Count_All'].rolling(window=window_size).mean()

    attack_data['Attack_Count_In_Radius_MA'] = attack_data['Count_In_Radius'].rolling(window=window_size).mean()
    baseline_data['Base_Count_In_Radius_MA'] = baseline_data['Count_In_Radius'].rolling(window=window_size).mean()

    # Calculate and print the recovery times for both subplots
    recovery_time_all = find_recovery_time(
        attack_data,
        baseline_data,
        'Attack_Count_All_MA',
        'Base_Count_All_MA',  # add this argument for the baseline data
        threshold_fraction,
        window_size,
        breakdown_time + breakdown_duration
    )

    recovery_time_in_radius = find_recovery_time(
        attack_data,
        baseline_data,
        'Attack_Count_In_Radius_MA',
        'Base_Count_In_Radius_MA',  # add this argument for the baseline data
        threshold_fraction,
        window_size,
        breakdown_time + breakdown_duration
    )

    # Calculate mean vehicle count during the breakdown duration for both scenarios from the raw data
    breakdown_end_time = breakdown_time + breakdown_duration

    # For all vehicles
    mean_count_during_breakdown_all_attack = attack_data.loc[
        (attack_data['Step'] >= breakdown_time) & (attack_data['Step'] <= breakdown_end_time), 'Count_All'].mean()
    mean_count_during_breakdown_all_baseline = baseline_data.loc[
        (baseline_data['Step'] >= breakdown_time) & (baseline_data['Step'] <= breakdown_end_time), 'Count_All'].mean()

    # For vehicles within the radius
    mean_count_during_breakdown_in_radius_attack = attack_data.loc[
        (attack_data['Step'] >= breakdown_time) & (attack_data['Step'] <= breakdown_end_time), 'Count_In_Radius'].mean()
    mean_count_during_breakdown_in_radius_baseline = baseline_data.loc[
        (baseline_data['Step'] >= breakdown_time) & (baseline_data['Step'] <= breakdown_end_time), 'Count_In_Radius'].mean()

    # Print the mean vehicle count during breakdown duration for both scenarios
    print(f"Attack scenario mean vehicle count during breakdown (All): {mean_count_during_breakdown_all_attack}")
    print(f"Baseline scenario mean vehicle count during breakdown (All): {mean_count_during_breakdown_all_baseline}")
    print(f"Attack scenario mean vehicle count during breakdown (In Radius): {mean_count_during_breakdown_in_radius_attack}")
    print(f"Baseline scenario mean vehicle count during breakdown (In Radius): {mean_count_during_breakdown_in_radius_baseline}")


    # Apply the Savitzky-Golay filter to smooth the data
    # Here, window_length should be odd and less than the length of the data
    # polyorder is the order of the polynomial used to fit the samples.
    # Adjust these parameters as needed.
    window_length, polyorder = 301, 3
    attack_data['Count_All_Smooth'] = savgol_filter(attack_data['Count_All'], window_length, polyorder)
    attack_data['Count_In_Radius_Smooth'] = savgol_filter(attack_data['Count_In_Radius'], window_length, polyorder)
    baseline_data['Count_All_Smooth'] = savgol_filter(baseline_data['Count_All'], window_length, polyorder)
    baseline_data['Count_In_Radius_Smooth'] = savgol_filter(baseline_data['Count_In_Radius'], window_length, polyorder)


    # Combine both dataframes
    combined_data = pd.concat([attack_data, baseline_data])

    # Plotting using seaborn
    plt.figure(figsize=(12, 6))

    # Count_All
    plt.subplot(2, 1, 1)
    sns.lineplot(data=combined_data, x='Step', y='Count_All_Smooth', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f'Count All in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    # Count_In_Radius
    plt.subplot(2, 1, 2)
    sns.lineplot(data=combined_data, x='Step', y='Count_In_Radius_Smooth', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f'Count In Radius in {scenario}')
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    plt.tight_layout()
    
    # Save the plot
    save_path = f"data/{project}/outputs/{scenario}/vehicle_count_comparison_plot.png"
    plt.savefig(save_path)
    plt.show()
    print(f"Plot saved to: {save_path}")

def find_recovery_time(attack_data, baseline_data, attack_ma_column_name, baseline_ma_column_name, threshold_fraction, attack_end_time):
    # Note: The function now expects the names of the pre-calculated moving average columns
    # as 'attack_ma_column_name' and 'baseline_ma_column_name'

    # Use the pre-calculated moving averages directly
    attack_ma = attack_data[attack_ma_column_name]
    baseline_ma = baseline_data[baseline_ma_column_name]

    # Find recovery time after the attack ends
    recovery_condition = (attack_ma >= (1 - threshold_fraction) * baseline_ma) & (attack_data['Step'] > attack_end_time)
    recovery_times = attack_data[recovery_condition]['Step']

    return recovery_times.iloc[0] if not recovery_times.empty else None

def print_recovery_times(recovery_time_all, recovery_time_in_radius):
    if recovery_time_all is not None:
        print(f"Recovery time for Mean_Speed_All: {recovery_time_all}")
    else:
        print("No recovery point found within the threshold for Mean_Speed_All after the attack.")

    if recovery_time_in_radius is not None:
        print(f"Recovery time for Mean_Speed_In_Radius: {recovery_time_in_radius}")
    else:
        print("No recovery point found within the threshold for Mean_Speed_In_Radius after the attack.")

# common functions

def plot_mean_density_vc_graphs(project, scenario, warmup_time, simulation_end_time, breakdown_time, breakdown_duration):
    # File paths
    attack_all_file_path = f"data/{project}/outputs/{scenario}/attack_lane_metrics_all_step.csv"
    baseline_all_file_path = f"data/{project}/outputs/{scenario}/base_lane_metrics_all_step.csv"

    # File paths
    attack_radius_file_path = f"data/{project}/outputs/{scenario}/attack_lane_metrics_in_radius_step.csv"
    baseline_radius_file_path = f"data/{project}/outputs/{scenario}/base_lane_metrics_in_radius_step.csv"

    # Load the data
    attack_all_data = pd.read_csv(attack_all_file_path)
    baseline_all_data = pd.read_csv(baseline_all_file_path)

    # Load the data
    attack_radius_data = pd.read_csv(attack_radius_file_path)
    baseline_radius_data = pd.read_csv(baseline_radius_file_path)

    window_size = 301  # for example, the size of the filter window
    poly_order = 3  # for example, the order of the polynomial used

    # Calculate the average density for each step for both datasets
    density_attack_all_data_avg = attack_all_data.groupby('Step')['Density'].mean().reset_index()
    density_attack_all_data_avg['Scenario'] = 'Attack'

    density_baseline_all_data_avg = baseline_all_data.groupby('Step')['Density'].mean().reset_index()
    density_baseline_all_data_avg['Scenario'] = 'Baseline'

    # Apply the Savitzky-Golay filter to the average density data
    density_attack_all_data_avg['Density'] = savgol_filter(density_attack_all_data_avg['Density'], window_size, poly_order)
    density_baseline_all_data_avg['Density'] = savgol_filter(density_baseline_all_data_avg['Density'], window_size, poly_order)

    density_all_combined = pd.concat([density_attack_all_data_avg, density_baseline_all_data_avg], ignore_index=True)

    # Calculate the average density for each step for both datasets
    density_attack_radius_data_avg = attack_radius_data.groupby('Step')['Density'].mean().reset_index()
    density_attack_radius_data_avg['Scenario'] = 'Attack'

    density_baseline_radius_data_avg = baseline_radius_data.groupby('Step')['Density'].mean().reset_index()
    density_baseline_radius_data_avg['Scenario'] = 'Baseline'

    # Define the start and end of the breakdown period
    breakdown_start = breakdown_time
    breakdown_end = breakdown_time + breakdown_duration

    # Filter the data for the breakdown period
    attack_all_breakdown = attack_all_data[(attack_all_data['Step'] >= breakdown_start) & (attack_all_data['Step'] <= breakdown_end)]
    baseline_all_breakdown = baseline_all_data[(baseline_all_data['Step'] >= breakdown_start) & (baseline_all_data['Step'] <= breakdown_end)]

    attack_radius_breakdown = attack_radius_data[(attack_radius_data['Step'] >= breakdown_start) & (attack_radius_data['Step'] <= breakdown_end)]
    baseline_radius_breakdown = baseline_radius_data[(baseline_radius_data['Step'] >= breakdown_start) & (baseline_radius_data['Step'] <= breakdown_end)]

    # Calculate mean density and V/C ratio during the breakdown period for all lanes
    mean_density_attack_all_breakdown = attack_all_breakdown['Density'].mean()
    mean_VC_ratio_attack_all_breakdown = attack_all_breakdown['VC_Ratio'].mean()

    mean_density_baseline_all_breakdown = baseline_all_breakdown['Density'].mean()
    mean_VC_ratio_baseline_all_breakdown = baseline_all_breakdown['VC_Ratio'].mean()

    # Calculate mean density and V/C ratio during the breakdown period for lanes within the radius
    mean_density_attack_radius_breakdown = attack_radius_breakdown['Density'].mean()
    mean_VC_ratio_attack_radius_breakdown = attack_radius_breakdown['VC_Ratio'].mean()

    mean_density_baseline_radius_breakdown = baseline_radius_breakdown['Density'].mean()
    mean_VC_ratio_baseline_radius_breakdown = baseline_radius_breakdown['VC_Ratio'].mean()

    # Output the means for all lanes
    print(f"During the breakdown period for all lanes:")
    print(f"Mean Density (Attack): {mean_density_attack_all_breakdown}")
    print(f"Mean V/C Ratio (Attack): {mean_VC_ratio_attack_all_breakdown}")
    print(f"Mean Density (Baseline): {mean_density_baseline_all_breakdown}")
    print(f"Mean V/C Ratio (Baseline): {mean_VC_ratio_baseline_all_breakdown}")

    # Output the means for lanes within the radius
    print(f"During the breakdown period for lanes within the radius:")
    print(f"Mean Density (Attack): {mean_density_attack_radius_breakdown}")
    print(f"Mean V/C Ratio (Attack): {mean_VC_ratio_attack_radius_breakdown}")
    print(f"Mean Density (Baseline): {mean_density_baseline_radius_breakdown}")
    print(f"Mean V/C Ratio (Baseline): {mean_VC_ratio_baseline_radius_breakdown}")


    # Apply the Savitzky-Golay filter to the average density data
    density_attack_radius_data_avg['Density'] = savgol_filter(density_attack_radius_data_avg['Density'], window_size, poly_order)
    density_baseline_radius_data_avg['Density'] = savgol_filter(density_baseline_radius_data_avg['Density'], window_size, poly_order)

    density_radius_combined = pd.concat([density_attack_radius_data_avg, density_baseline_radius_data_avg], ignore_index=True)

    # Plotting using seaborn
    plt.figure(figsize=(14,10))

    plt.subplot(2, 1, 1)
    sns.lineplot(data=density_all_combined, x='Step', y='Density', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f"Mean lane Density vs Step in All in {scenario}")
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    plt.subplot(2, 1, 2)
    sns.lineplot(data=density_radius_combined, x='Step', y='Density', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f"Mean lane Density vs Step in Radius in {scenario}")
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    plt.tight_layout()
    
    # Save the plot
    save_path = f"data/{project}/outputs/{scenario}/lane_density_comparison_plot.png"
    plt.savefig(save_path)
    plt.show()
    print(f"Plot saved to: {save_path}")


    # Calculate the average VC_Ratio for each step for both datasets
    VC_Ratio_attack_all_data_avg = attack_all_data.groupby('Step')['VC_Ratio'].mean().reset_index()
    VC_Ratio_attack_all_data_avg['Scenario'] = 'Attack'

    VC_Ratio_baseline_all_data_avg = baseline_all_data.groupby('Step')['VC_Ratio'].mean().reset_index()
    VC_Ratio_baseline_all_data_avg['Scenario'] = 'Baseline'

    # Apply the Savitzky-Golay filter to the average VC_Ratio data
    VC_Ratio_attack_all_data_avg['VC_Ratio'] = savgol_filter(VC_Ratio_attack_all_data_avg['VC_Ratio'], window_size, poly_order)
    VC_Ratio_baseline_all_data_avg['VC_Ratio'] = savgol_filter(VC_Ratio_baseline_all_data_avg['VC_Ratio'], window_size, poly_order)

    VC_Ratio_all_combined = pd.concat([VC_Ratio_attack_all_data_avg, VC_Ratio_baseline_all_data_avg], ignore_index=True)

    # Calculate the average VC_Ratio for each step for both datasets
    VC_Ratio_attack_radius_data_avg = attack_radius_data.groupby('Step')['VC_Ratio'].mean().reset_index()
    VC_Ratio_attack_radius_data_avg['Scenario'] = 'Attack'

    VC_Ratio_baseline_radius_data_avg = baseline_radius_data.groupby('Step')['VC_Ratio'].mean().reset_index()
    VC_Ratio_baseline_radius_data_avg['Scenario'] = 'Baseline'

    # Apply the Savitzky-Golay filter to the average VC_Ratio data
    VC_Ratio_attack_radius_data_avg['VC_Ratio'] = savgol_filter(VC_Ratio_attack_radius_data_avg['VC_Ratio'], window_size, poly_order)
    VC_Ratio_baseline_radius_data_avg['VC_Ratio'] = savgol_filter(VC_Ratio_baseline_radius_data_avg['VC_Ratio'], window_size, poly_order)

    VC_Ratio_radius_combined = pd.concat([VC_Ratio_attack_radius_data_avg, VC_Ratio_baseline_radius_data_avg], ignore_index=True)

    # Plotting using seaborn
    plt.figure(figsize=(14,10))

    plt.subplot(2, 1, 1)
    sns.lineplot(data=VC_Ratio_all_combined, x='Step', y='VC_Ratio', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f"Mean lane VC_Ratio vs Step in All in {scenario}")
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    plt.subplot(2, 1, 2)
    sns.lineplot(data=VC_Ratio_radius_combined, x='Step', y='VC_Ratio', hue='Scenario', errorbar=None, palette={'Attack': 'red', 'Baseline': 'blue'})
    plt.title(f"Mean lane VC_Ratio vs Step in Radius in {scenario}")
    plt.xlim(warmup_time, simulation_end_time)  # Add this line to set x-axis limits
    plt.axvline(x=breakdown_time, color='black', linestyle='--') 
    plt.axvline(x=breakdown_time + breakdown_duration, color='black', linestyle='--')

    # After plotting, get the y-axis limits:
    ymin, ymax = plt.ylim()
    # Adjust ymin and ymax to extend the shading area:
    padding = 0.05  # This can be adjusted based on the desired extension
    ymin -= padding
    ymax += padding
    # Set the new y-axis limits:
    plt.ylim(ymin, ymax)
    # Fill the area between the vertical lines:
    plt.fill_between([breakdown_time, breakdown_time + breakdown_duration], ymin, ymax, color='pink', alpha=0.2)

    # Calculate the midpoint of the shaded region for the x-coordinate
    x_center = (breakdown_time + breakdown_time + breakdown_duration) / 2

    # Get the current y-axis limits for calculating the y-coordinate
    ymin, ymax = plt.ylim()
    y_center = (ymin + ymax) / 2

    # Add centered text
    plt.text(x_center, y_center, 'Cyberattack duration', horizontalalignment='center', verticalalignment='center', alpha=0.5)

    plt.tight_layout()
    
    # Save the plot
    save_path = f"data/{project}/outputs/{scenario}/VC_ratio_comparison_plot.png"
    plt.savefig(save_path)
    plt.show()
    print(f"Plot saved to: {save_path}")

def scenario_network_visualization(net_file, scenario, project, xml_file, draw_circles):
    # Parse the network XML
    tree = ET.parse(net_file)
    root = tree.getroot()

    # Read the edges from the XML file
    edge_file = f'data/{project}/outputs/{scenario}/{xml_file}.xml'
    edge_tree = ET.parse(edge_file)
    edge_root = edge_tree.getroot()

    # Check the root element to determine the XML format
    red_edges = []
    if edge_root.tag == 'RadiusEdges':
        # Old format
        red_edges = [edge.get('id') for edge in edge_root.findall('Edge')]
    elif edge_root.tag == 'Incidents':
        # New format
        for incident in edge_root.findall('Incident'):
            incident_edges = [edge.get('id') for edge in incident.findall('Edge')]
            red_edges.extend(incident_edges)

    vehicle_positions = []
    vehicle_file = f'data/{project}/outputs/{scenario}/stopped_vehicles.csv'
    with open(vehicle_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            vehicle_positions.append({
                'vehicle_id': row['vehicle_id'],
                'slowdown_issued': float(row['slowdown_issued']),
                'actual_stop_time': float(row['actual_stop_time']),
                'position_x': float(row['position_x']),
                'position_y': float(row['position_y'])
            })

    # Set the figure size (width, height)
    plt.figure(figsize=(20,20))

    # Plot network lanes by iterating over edges
    for edge in root.findall(".//edge"):
        edge_id = edge.get('id')
        for lane in edge.findall(".//lane"):
            shape = lane.get("shape").split()
            x_coords, y_coords = zip(*[map(float, coord.split(",")) for coord in shape])
            
            # Check if the current edge ID is in the list of red edges
            if edge_id in red_edges:
                plt.plot(x_coords, y_coords, color='red', linewidth=3)
            else:
                plt.plot(x_coords, y_coords, color='grey', linewidth=2)

    # Option to toggle circle drawing
    draw_circles = RADIUS_VISUAL  # Set to False if you don't want to draw circles around vehicle dots

    # Plot vehicle positions AFTER plotting network lanes
    first_vehicle = True
    for vehicle in vehicle_positions:
        plt.scatter(vehicle['position_x'], vehicle['position_y'], color='darkred', s=50, zorder=3, label='Attacked vehicles' if first_vehicle else "_nolegend_")
        first_vehicle = False
        
        if draw_circles == True:
            circle = plt.Circle((vehicle['position_x'], vehicle['position_y']), RADIUS, color='darkred', fill=False, zorder=2)
            plt.gca().add_artist(circle)

    # Create legend items manually
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Attacked vehicles',
            markerfacecolor='darkred', markersize=10)
    ]

    # Add a legend for the catchment area circle
    if draw_circles:
        legend_elements.append(
            Line2D([0], [0], marker='o', color='w', label=f'Catchment area for r={RADIUS}m',
                markerfacecolor='none', markeredgecolor='darkred', markersize=10)
        )

    # Add the custom legend to the plot with the created legend elements
    plt.legend(handles=legend_elements, loc='best')

    # Set aspect ratio
    plt.gca().set_aspect('equal', adjustable='box')

    # Calculate the range of x and y coordinates
    all_x_coords = []
    all_y_coords = []
    for edge in root.findall(".//edge"):
        for lane in edge.findall(".//lane"):
            shape = lane.get("shape").split()
            x_coords, y_coords = zip(*[map(float, coord.split(",")) for coord in shape])
            all_x_coords.extend(x_coords)
            all_y_coords.extend(y_coords)

    # Apply a plot buffer
    buffer = 100  # Example buffer of 10%
    x_min, x_max = min(all_x_coords), max(all_x_coords)
    y_min, y_max = min(all_y_coords), max(all_y_coords)

    # Set plot limits with the buffer
    plt.xlim(x_min - buffer, x_max + buffer)
    plt.ylim(y_min - buffer, y_max + buffer)

    # Optional zoom (replace with your desired coordinates if needed)
    use_zoom = False  # Set to True if zoom is needed
    if use_zoom:
        min_x, max_x = -100, 100
        min_y, max_y = -100, 100
        plt.xlim([min_x, max_x])
        plt.ylim([min_y, max_y])

    # Label the axes
    plt.xlabel('Easting (m)')
    plt.ylabel('Northing (m)')

    plt.tight_layout(pad=5.0)  # The padding can be adjusted as needed.

    # Save the matplotlib plot as PDF
    plt.savefig(f'data/{project}/outputs/{scenario}/{xml_file}.pdf', format='pdf', dpi=300)

    # Display the matplotlib plot
    plt.show()


def interpolate_position_along_edge(x_coords, y_coords, position, edge_length):
    if position > edge_length:
        return x_coords[-1], y_coords[-1]

    distance_covered = 0
    for i in range(1, len(x_coords)):
        segment_length = ((x_coords[i] - x_coords[i - 1])**2 + (y_coords[i] - y_coords[i - 1])**2)**0.5
        if distance_covered + segment_length >= position:
            ratio = (position - distance_covered) / segment_length
            x = x_coords[i - 1] + ratio * (x_coords[i] - x_coords[i - 1])
            y = y_coords[i - 1] + ratio * (y_coords[i] - y_coords[i - 1])
            return x, y
        distance_covered += segment_length

    return x_coords[0], y_coords[0]

def scenario_network_visualization_with_detectors(net_file, scenario, project, xml_file):
    # Parse the network XML
    tree = ET.parse(net_file)
    root = tree.getroot()

    # Read the detectors from the XML file
    edge_file = f'data/{project}/outputs/{scenario}/{xml_file}.xml'
    edge_tree = ET.parse(edge_file)
    edge_root = edge_tree.getroot()
    detectors = []
    for detector in edge_root.findall('Detector'):
        edge_id = detector.get('edge')
        position = float(detector.get('position'))
        detectors.append((edge_id, position))

    plt.figure(figsize=(20,20))

    # Plot network lanes by iterating over edges
    for edge in root.findall(".//edge"):
        edge_id = edge.get('id')
        for lane in edge.findall(".//lane"):
            shape = lane.get("shape").split()
            x_coords, y_coords = zip(*[map(float, coord.split(",")) for coord in shape])
            plt.plot(x_coords, y_coords, color='grey', linewidth=2)

            # Plot detectors for this edge
            for det_edge_id, det_pos in detectors:
                if det_edge_id == edge_id:
                    edge_length = sum([((x_coords[i] - x_coords[i - 1])**2 + (y_coords[i] - y_coords[i - 1])**2)**0.5 for i in range(1, len(x_coords))])
                    det_x, det_y = interpolate_position_along_edge(x_coords, y_coords, det_pos, edge_length)
                    plt.scatter(det_x, det_y, color='blue', s=70, marker='x', zorder=4)

    plt.gca().set_aspect('equal', adjustable='box')
    plt.xlabel('Easting (m)')
    plt.ylabel('Northing (m)')
    plt.tight_layout(pad=5.0)
    plt.savefig(f'data/{project}/outputs/{scenario}/network_with_detectors.pdf', format='pdf', dpi=300)
    plt.show()

# Call the function with appropriate parameters



# Deprecated functions
def run_plot_net_selection(net_file, scenario, project): # using scenario_network_visualization() instead
    """
    Runs the plot_net_selection.py script using the given input and net files.

    Parameters:
    - input_file: The path to the edges_near_stopped_egos.txt or other input file.
    - net_file: The path to the .net.xml file.
    """
    script_path = os.environ.get("SUMO_TOOLS_PATH", ".././env/lib/python3.10/site-packages/sumo/tools")
    script_file = "visualization/plot_net_selection.py"
    full_path = os.path.join(script_path, script_file)

    edge_color = "#606060"
    selected_color = "#800000"

    input_file = f'data/{project}/outputs/{scenario}/edges_near_stopped_egos.txt'

    cmd = ["python", full_path, "-n", net_file, "-i", input_file, "--edge-color", edge_color, "--selected-color", selected_color, "--dpi", "1000"]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":

    # combine_speeds_and_counts(project=PROJECT, scenario=SCENARIO)
    # mean_speeds_and_counts(project=PROJECT, scenario=SCENARIO, warmup_time=WARMUP_TIME, simulation_end_time=SIMULATION_END_TIME, breakdown_time=BREAKDOWN_TIME, breakdown_duration=BREAKDOWN_DURATION)  

    # scenario_network_visualization(net_file=NET_FILE_PATH, scenario=SCENARIO, project=PROJECT, xml_file='radius_edges', draw_circles=RADIUS_VISUAL)
    scenario_network_visualization(net_file=NET_FILE_PATH, scenario=SCENARIO, project=PROJECT, xml_file= 'upstream_edges', draw_circles=False)
    scenario_network_visualization_with_detectors(net_file=NET_FILE_PATH, scenario=SCENARIO, project=PROJECT, xml_file= 'upstream_edges')

    # plot_mean_speed_graph(project=PROJECT, scenario=SCENARIO, warmup_time=WARMUP_TIME, simulation_end_time=SIMULATION_END_TIME, breakdown_time=BREAKDOWN_TIME, breakdown_duration=BREAKDOWN_DURATION)
    # plot_vehicle_count_graph(project=PROJECT, scenario=SCENARIO, warmup_time=WARMUP_TIME, simulation_end_time=SIMULATION_END_TIME, breakdown_time=BREAKDOWN_TIME, breakdown_duration=BREAKDOWN_DURATION)
    # plot_mean_density_vc_graphs(project=PROJECT, scenario=SCENARIO, warmup_time=WARMUP_TIME, simulation_end_time=SIMULATION_END_TIME, breakdown_time=BREAKDOWN_TIME, breakdown_duration=BREAKDOWN_DURATION)


