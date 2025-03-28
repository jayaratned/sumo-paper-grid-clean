import traci
import numpy as np
import csv
import os
from .vehicle_utils import get_edges_near_stopped_egos
import xml.etree.ElementTree as ET

# Initialize dictionaries outside the function to maintain state between function calls
cumulative_metrics_all = {}
cumulative_metrics_in_radius = {}

# Traffic data collection functions
def collect_and_save_mean_speeds(radius, warmup_time, baseline=False, scenario=None, project=None):

    step = traci.simulation.getTime()

    if step < warmup_time:
        return

    vehicle_ids = traci.vehicle.getIDList()
    speeds_all = get_speeds_of_vehicles(vehicle_ids)
    mean_speed_all = np.mean(speeds_all) if speeds_all else 0

    edges_of_interest = read_edges_from_xml(f'data/{project}/outputs/{scenario}/radius_edges.xml')
    # edges_of_interest = read_edges_from_file(f'data/{project}/outputs/{scenario}/edges_near_stopped_egos.txt')
    vehicles_in_radius = [veh_id for veh_id in vehicle_ids if traci.vehicle.getRoadID(veh_id) in edges_of_interest]
    speeds_in_radius = get_speeds_of_vehicles(vehicles_in_radius)
    mean_speed_in_radius = np.mean(speeds_in_radius) if speeds_in_radius else 0

    # Modify the filename based on baseline value
    filename_prefix = 'base' if baseline else 'attack'
    output_directory = os.path.join('data', project, 'outputs', scenario)
    ensure_directory_exists(output_directory)
    output_filename = os.path.join(output_directory, f'{filename_prefix}_mean_speeds.csv')

    # Save to CSV
    save_to_csv(
        output_filename,
        ['Step', 'Mean_Speed_All', 'Mean_Speed_In_Radius'],
        [{'Step': step, 'Mean_Speed_All': mean_speed_all, 'Mean_Speed_In_Radius': mean_speed_in_radius}]
    )
def collect_and_save_vehicle_count(radius, warmup_time, baseline=False, scenario=None, project=None):
    
    step = traci.simulation.getTime()
    if step < warmup_time:
        return

    vehicle_ids = traci.vehicle.getIDList()
    count_all = len(vehicle_ids)

    edges_of_interest = read_edges_from_xml(f'data/{project}/outputs/{scenario}/radius_edges.xml')
    # edges_of_interest = read_edges_from_file(f'data/{project}/outputs/{scenario}/edges_near_stopped_egos.txt')
    count_in_radius = get_vehicle_count_on_edges(vehicle_ids, edges_of_interest)

    # Modify the filename based on baseline value
    filename_prefix = 'base' if baseline else 'attack'
    output_directory = os.path.join('data', project, 'outputs', scenario)
    ensure_directory_exists(output_directory)
    output_filename = os.path.join(output_directory, f'{filename_prefix}_vehicle_counts.csv')

    # Save to CSV
    save_to_csv(
        output_filename,
        ['Step', 'Count_All', 'Count_In_Radius'],
        [{'Step': step, 'Count_All': count_all, 'Count_In_Radius': count_in_radius}]
    )
def collect_and_save_mean_edge_delays_over_simulation(radius, warmup_time, baseline=False, last_sim_step=None, scenario=None, project=None, ego_type='ego'):
    """Collect cumulative edge delays over the simulation and save the means at the end."""
    
    step = traci.simulation.getTime()
    if step < warmup_time:
        return

    # Initialize dictionaries to store cumulative delays and counts
    cumulative_delays_all = {}
    cumulative_delays_in_radius = {}
    
    # Collect the edge IDs and filter out internal edges (part of intersections)
    edge_ids = [edge_id for edge_id in traci.edge.getIDList() if not edge_id.startswith(":")]

    edges_of_interest = read_edges_from_xml(f'data/{project}/outputs/{scenario}/radius_edges.xml')
    # edges_of_interest = read_edges_from_file(f'data/{project}/outputs/{scenario}/edges_near_stopped_egos.txt')

    for edge_id in edge_ids:
        # Get the first lane of the edge
        lane_id = edge_id + "_0"  # Assuming lane indexing starts at 0
        edge_speed_limit = traci.lane.getMaxSpeed(lane_id)
        
        # Get vehicles on this edge
        vehicles_on_edge = traci.edge.getLastStepVehicleIDs(edge_id)
        
        # Calculate delay for each vehicle on the edge
        delays_on_edge = [max(0, edge_speed_limit - traci.vehicle.getSpeed(veh_id)) for veh_id in vehicles_on_edge if traci.vehicle.getSpeed(veh_id) is not None]

        
        # Update cumulative delays and counts
        if edge_id not in cumulative_delays_all:
            cumulative_delays_all[edge_id] = {'total': 0, 'count': 0}
        cumulative_delays_all[edge_id]['total'] += sum(delays_on_edge)
        cumulative_delays_all[edge_id]['count'] += len(delays_on_edge)

        # Check if the edge is within radius and update accordingly
        if edge_id in edges_of_interest:
            if edge_id not in cumulative_delays_in_radius:
                cumulative_delays_in_radius[edge_id] = {'total': 0, 'count': 0}
            cumulative_delays_in_radius[edge_id]['total'] += sum(delays_on_edge)
            cumulative_delays_in_radius[edge_id]['count'] += len(delays_on_edge)

  # If at the end of the simulation, compute means and save to CSV
    if step == last_sim_step:
        # Compute mean delays
        mean_delays_all = {edge: data['total'] / data['count'] if data['count'] != 0 else 0 for edge, data in cumulative_delays_all.items()}
        mean_delays_in_radius = {edge: data['total'] / data['count'] if data['count'] != 0 else 0 for edge, data in cumulative_delays_in_radius.items()}

        # Modify the filename based on baseline value
        filename_prefix = 'base' if baseline else 'attack'
        output_directory = os.path.join('data', project, 'outputs', scenario)
        ensure_directory_exists(output_directory)
        output_filename_all = os.path.join(output_directory, f'{filename_prefix}_mean_edge_delays_all.csv')
        output_filename_in_radius = os.path.join(output_directory, f'{filename_prefix}_mean_edge_delays_radius.csv')

        
        # Save to CSV using the existing save_to_csv function
        save_to_csv(output_filename_all, ['Edge', 'Mean_Delay'], [{'Edge': edge, 'Mean_Delay': delay} for edge, delay in mean_delays_all.items()])
        save_to_csv(output_filename_in_radius, ['Edge', 'Mean_Delay'], [{'Edge': edge, 'Mean_Delay': delay} for edge, delay in mean_delays_in_radius.items()])
def collect_and_save_lane_metrics(radius, warmup_time, last_sim_step=None, baseline=False, scenario=None, input_capacity=1700, project=None):
    """
    Collects and saves lane metrics for a SUMO simulation.

    Args:
        radius (float): The radius around stopped egos to consider.
        warmup_time (int): The number of simulation steps to wait before collecting data.
        last_sim_step (int, optional): The last simulation step to collect data for. Defaults to None.
        baseline (bool, optional): Whether this is a baseline simulation. Defaults to False.
        scenario (str, optional): The name of the scenario being simulated. Defaults to None.
        input_capacity (int, optional): The input capacity of the simulation. Defaults to 1700.
        project (str, optional): The name of the project. Defaults to None.
    """
    step = traci.simulation.getTime()
    if step < warmup_time:
        return

    edges_of_interest = read_edges_from_xml(f'data/{project}/outputs/{scenario}/radius_edges.xml')
    # edges_of_interest = read_edges_from_file(f'data/{project}/outputs/{scenario}/edges_near_stopped_egos.txt')
    
    # Get all edges (excluding those that start with ":")
    all_edges = [edge for edge in traci.edge.getIDList() if not edge.startswith(":")]

    data_all = []
    data_in_radius = []
    for edge in all_edges:
        lane_id = edge + "_0"  # Assuming a single lane per edge.
        speed = get_average_lane_speed(lane_id)
        density = get_lane_density(lane_id)
        vc_ratio = get_vc_ratio(lane_id, input_capacity)
        
        data_point = {
            'Step': step,
            'Lane': lane_id,
            'Speed': speed,
            'Density': density,
            'VC_Ratio': vc_ratio
        }

        data_all.append(data_point)

        if edge in edges_of_interest:
            data_in_radius.append(data_point)

        # Cumulative metric calculations for end of simulation
        if lane_id not in cumulative_metrics_all:
            cumulative_metrics_all[lane_id] = {'total_speed': 0, 'total_density': 0, 'total_vc_ratio': 0, 'count': 0}
            
        cumulative_metrics_all[lane_id]['total_speed'] += speed
        cumulative_metrics_all[lane_id]['total_density'] += density
        cumulative_metrics_all[lane_id]['total_vc_ratio'] += vc_ratio
        cumulative_metrics_all[lane_id]['count'] += 1

        if edge in edges_of_interest:
            if lane_id not in cumulative_metrics_in_radius:
                cumulative_metrics_in_radius[lane_id] = {'total_speed': 0, 'total_density': 0, 'total_vc_ratio': 0, 'count': 0}
            
            cumulative_metrics_in_radius[lane_id]['total_speed'] += speed
            cumulative_metrics_in_radius[lane_id]['total_density'] += density
            cumulative_metrics_in_radius[lane_id]['total_vc_ratio'] += vc_ratio
            cumulative_metrics_in_radius[lane_id]['count'] += 1

    # Save data for this simulation step
    filename_prefix = 'base' if baseline else 'attack'
    output_directory = os.path.join('data', project, 'outputs', scenario)
    ensure_directory_exists(output_directory)
    
    output_filename_all_step = os.path.join(output_directory, f'{filename_prefix}_lane_metrics_all_step.csv')
    output_filename_in_radius_step = os.path.join(output_directory, f'{filename_prefix}_lane_metrics_in_radius_step.csv')

    save_to_csv(output_filename_all_step, ['Step', 'Lane', 'Speed', 'Density', 'VC_Ratio'], data_all, append=True)
    save_to_csv(output_filename_in_radius_step, ['Step', 'Lane', 'Speed', 'Density', 'VC_Ratio'], data_in_radius, append=True)

    # If at the end of the simulation, compute means and save to CSV
    if step == last_sim_step:
        mean_metrics_all = {lane: {'Speed': data['total_speed'] / data['count'],
                                   'Density': data['total_density'] / data['count'],
                                   'VC_Ratio': data['total_vc_ratio'] / data['count']}
                            for lane, data in cumulative_metrics_all.items()}
        
        mean_metrics_in_radius = {lane: {'Speed': data['total_speed'] / data['count'],
                                         'Density': data['total_density'] / data['count'],
                                         'VC_Ratio': data['total_vc_ratio'] / data['count']}
                                  for lane, data in cumulative_metrics_in_radius.items()}

        output_filename_all = os.path.join(output_directory, f'{filename_prefix}_mean_lane_metrics_all.csv')
        output_filename_in_radius = os.path.join(output_directory, f'{filename_prefix}_mean_lane_metrics_radius.csv')

        # Save to CSV using the existing save_to_csv function
        save_to_csv(output_filename_all, ['Lane', 'Speed', 'Density', 'VC_Ratio'],
                    [{'Lane': lane, **metrics} for lane, metrics in mean_metrics_all.items()])
        
        save_to_csv(output_filename_in_radius, ['Lane', 'Speed', 'Density', 'VC_Ratio'],
                    [{'Lane': lane, **metrics} for lane, metrics in mean_metrics_in_radius.items()])

# Network isolation functions
def get_gridlocked_edges(stop_time, warmup_time, scenario=None, project=None):
    """
    Identify edges in gridlock and save them to a CSV.
    
    Parameters:
    - stop_time: Time the egos stopped.
    - scenario: The name of the scenario being simulated.

    Returns:
    - A dictionary with edge_id as the key and time taken to enter gridlock as the value.
    """
    step = traci.simulation.getTime()
    if step < warmup_time:
        return
    
    GRIDLOCK_SPEED_THRESHOLD = 5 / 3.6  # 5 km/h in m/s
    output_directory = os.path.join('data', project, 'outputs', scenario)
    ensure_directory_exists(output_directory)
    output_filename = os.path.join(output_directory, 'gridlocked_edges.csv')

    gridlocked_edges = {}

    # Collect the edge IDs and filter out internal edges (part of intersections)
    edge_ids = [edge_id for edge_id in traci.edge.getIDList() if not edge_id.startswith(":")]

    data_to_save = []

    for edge_id in edge_ids:
        num_vehicles = traci.edge.getLastStepVehicleNumber(edge_id)
        
        # Check if the edge has vehicles
        if num_vehicles > 0:
            mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)

            # If the mean speed is below the threshold, consider this lane as gridlocked
            if mean_speed < GRIDLOCK_SPEED_THRESHOLD:
                time_into_gridlock = step - stop_time
                gridlocked_edges[edge_id] = time_into_gridlock

                data_to_save.append({
                    'Edge': edge_id,
                    'Time_Into_Gridlock': time_into_gridlock
                })

    # Save gridlocked edges data to CSV
    save_to_csv(
        output_filename,
        ['Edge', 'Time_Into_Gridlock'],
        data_to_save,
        append=True
    )

    return gridlocked_edges

# Supporting functions
def ensure_directory_exists(directory):
    """Ensure that a directory exists. If it doesn't, create it."""
    if not os.path.exists(directory):
        os.makedirs(directory)
def get_speeds_of_vehicles(vehicle_ids):
    """Retrieve speeds of the specified vehicles."""
    return [traci.vehicle.getSpeed(veh_id) * 3.6 for veh_id in vehicle_ids]
def get_vehicle_count_on_edges(vehicle_ids, edges_of_interest):
    """Count vehicles on specified edges."""
    return sum(1 for veh_id in vehicle_ids if traci.vehicle.getRoadID(veh_id) in edges_of_interest)
def read_edges_from_file(filename):
    """Read edges from a file."""
    with open(filename, 'r') as file:
        return [line.strip().split(":")[1] for line in file]
def save_to_csv(filename, fieldnames, data, append=True):
    """Save data to a CSV file."""

    # Check if file exists
    file_exists = os.path.isfile(filename)
    mode = 'a' if append else 'w'  # Use append mode if append=True, otherwise use write mode

    with open(filename, mode, newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write the header only if we're not appending, or if the file didn't exist before
        if not append or (append and not file_exists):
            writer.writeheader()
        
        for row in data:
            writer.writerow(row)
def get_average_lane_speed(lane_id):
    """Return the average speed of vehicles on a lane."""
    return traci.lane.getLastStepMeanSpeed(lane_id) * 3.6
def get_lane_density(lane_id):
    """Return the density of vehicles on a lane (vehicles per meter)."""
    vehicle_count = traci.lane.getLastStepVehicleNumber(lane_id)
    lane_length = traci.lane.getLength(lane_id) / 1000  # Convert to km
    return vehicle_count / lane_length
def get_vc_ratio(lane_id, capacity):
    """Return the volume to capacity ratio for a lane."""
    flow = get_average_lane_speed(lane_id) * get_lane_density(lane_id)
    return flow / capacity

# read edges from file - but its xml!
def read_edges_from_xml(filename):
    """Read edges from an XML file."""
    tree = ET.parse(filename)
    root = tree.getroot()

    edges = [edge.get('id') for edge in root.findall('Edge')]
    return edges