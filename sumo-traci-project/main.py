"""
This script runs a SUMO simulation with or without attack scenario (ego breakdown) features.
It reads settings from a configuration file and initializes the SUMO environment.
It registers several observers to collect and save various metrics during the simulation.
If ego breakdown feature is enabled, it also registers observers to stop egos and identify nearby edges.
After running the simulation, it writes the edges near stopped egos to a file.
Finally, it post-processes simulation results including plotting and visualization.
"""
from utils import sumo_utils as su
from utils import vehicle_utils as vu
from utils import visualization_utils as visu
from utils import data_utils as du
from utils import detector_utils as detu
import configparser
import sumolib
import traci

# Read settings from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Simulation settings
EDGE_DETECTION = config.getboolean('Simulation', 'edge_detection') # this is a new setting for edge detection only

SCENARIO = config['Simulation']['scenario']
SUMO_GUI = config.getboolean('Simulation', 'sumo_gui')
WARMUP_TIME = int(config['Simulation']['warmup_time'])
SIMULATION_END_TIME = int(config['Simulation']['end_time'])
RADIUS = int(config['Simulation']['radius'])
UPSTREAM = int(config['Simulation']['upstream'])
CAPACITY_PER_HOUR = int(config['Simulation']['lane_capacity'])
ego_BREAKDOWN_ENABLED = config.getboolean('Simulation', 'ego_breakdown_enabled')
ego_BREAKDOWN_TIME = int(config['Simulation']['ego_breakdown_time'])
ego_BREAKDOWN_DURATION = int(config['Simulation']['ego_breakdown_duration'])
ego_TYPE = config['Simulation']['ego_type']
PARTIAL_INCLUSION = config.getboolean('Simulation', 'partial_edge_inclusion')

# Files settings
PROJECT = config['Files']['Project']
NET_FILE_PATH = config['Files']['Net_File_Path']
net = sumolib.net.readNet(NET_FILE_PATH, withInternal=True)
CONFIG_FILE = config['Files']['Config_File_Path'] # read the value of the "Config_File_Path" key from the "Files" section of the configuration file

# Visualization settings
PLOT_SMOOTHING = config.getboolean('Visualization', 'Smoothing')
PLOT_INTERVAL = int(config['Visualization']['Interval'])

accumulated_data = {}

# print to terminal to identify attack/ baseline scenario
if EDGE_DETECTION:
    print("Running edge detection mode")
else:
    if ego_BREAKDOWN_ENABLED:
        print("Running attack scenario")
        BASELINE_SCENARIO = False
    else:
        print("Running baseline scenario")
        BASELINE_SCENARIO = True

def setup_simulation() -> None:
    """Initializes the SUMO environment."""
    su.setup_sumo(sumo_gui=SUMO_GUI, sumo_config_file=CONFIG_FILE)

def run_main_simulation() -> None:
    """
    Runs the main SUMO simulation with or without attack scenario (ego breakdown) features.
    
    This function registers several observers to collect and save various metrics during the simulation.
    If ego breakdown feature is enabled, it also registers observers to stop egos and identify nearby edges.
    After running the simulation, it writes the edges near stopped egos to a file.
    """
    nearby_edges = set()
    

    # Egde detection only
    if EDGE_DETECTION:
        
        # Register observer for edge detection
        su.register_observer(lambda: vu.stop_all_egos_at_current_position(ego_BREAKDOWN_TIME, ego_BREAKDOWN_TIME + 60, ego_TYPE))
        su.register_observer(lambda: nearby_edges.update(vu.get_edges_near_stopped_egos(RADIUS, ego_TYPE)))
    
        # Run the simulation
        su.run_simulation(ego_BREAKDOWN_TIME + 60) # run for 60 seconds after the ego breakdown

        # vu.write_edges_to_file(nearby_edges, scenario=SCENARIO, project=PROJECT) # Write the edges near stopped egos to a file
        vu.save_radius_edges_as_xml(nearby_edges, scenario=SCENARIO, project=PROJECT)

        vu.write_stopped_vehicles_to_file(scenario=SCENARIO, project=PROJECT) # Write the stopped vehicles to a file
        path_to_stopped_vehicles_file = f'data/{PROJECT}/outputs/{SCENARIO}/stopped_vehicles.csv'
        upstream_edges, edge_tags = vu.get_upstream_edges_with_distance(path_to_stopped_vehicles_file, net, distance_limit=UPSTREAM, partial_inclusion=PARTIAL_INCLUSION)
        vu.save_upstream_edges_as_xml(upstream_edges, scenario=SCENARIO, project=PROJECT)
        vu.save_upstream_edge_tags_as_xml(edge_tags, scenario=SCENARIO, project=PROJECT)

        # save config file to output directory
        output_dir = f'data/{PROJECT}/outputs/{SCENARIO}'
        su.save_config_file(CONFIG_FILE, output_dir)

    else:
    
        # Register common observer for both cases
        su.register_observer(lambda: du.collect_and_save_mean_speeds(radius=RADIUS, warmup_time=WARMUP_TIME, baseline=BASELINE_SCENARIO, scenario=SCENARIO, project=PROJECT))
        su.register_observer(lambda: du.collect_and_save_vehicle_count(radius=RADIUS, warmup_time=WARMUP_TIME, baseline=BASELINE_SCENARIO, scenario=SCENARIO, project=PROJECT))
        su.register_observer(lambda: du.collect_and_save_mean_edge_delays_over_simulation(radius=RADIUS, warmup_time=WARMUP_TIME, baseline=BASELINE_SCENARIO, last_sim_step=SIMULATION_END_TIME, scenario=SCENARIO, project=PROJECT, ego_type=ego_TYPE))
        su.register_observer(lambda: du.collect_and_save_lane_metrics(radius=RADIUS, warmup_time=WARMUP_TIME, last_sim_step=SIMULATION_END_TIME, baseline=BASELINE_SCENARIO, scenario=SCENARIO, input_capacity=CAPACITY_PER_HOUR, project=PROJECT))
        su.register_observer(lambda: du.get_gridlocked_edges(stop_time=ego_BREAKDOWN_TIME, warmup_time=WARMUP_TIME, scenario=SCENARIO, project=PROJECT))
        su.register_observer(lambda: detu.simulate_detectors(detectors, accumulated_data, traci.simulation.getTime()))

        if ego_BREAKDOWN_ENABLED:
            # Register observers for stopping egos and identifying nearby edges
            su.register_observer(lambda: vu.stop_all_egos_at_current_position(ego_BREAKDOWN_TIME, ego_BREAKDOWN_DURATION, ego_TYPE))
            # su.register_observer(lambda: nearby_edges.update(vu.get_edges_near_stopped_egos(RADIUS)))

        # Adding detectors
        edge_ids = detu.get_edge_ids_from_xml(f'data/{PROJECT}/outputs/{SCENARIO}/upstream_edges.xml')
        detectors = detu.calculate_detector_positions(net, edge_ids, 50) 
        detu.save_detectors_to_xml(detectors, scenario=SCENARIO, project=PROJECT) 

        # Run the simulation
        su.run_simulation(SIMULATION_END_TIME)
        
        # if ego_BREAKDOWN_ENABLED:
        #     # Write the edges near stopped egos to a file
        #     vu.write_edges_to_file(nearby_edges, scenario=SCENARIO, project=PROJECT)

def post_process_results() -> None: 
    """Post-processes simulation results including plotting and visualization."""
    if not EDGE_DETECTION:
        if ego_BREAKDOWN_ENABLED:
            detu.write_detector_data_to_csv(accumulated_data, f'data/{PROJECT}/outputs/{SCENARIO}/attack_detector_data.csv')
        else:
            detu.write_detector_data_to_csv(accumulated_data, f'data/{PROJECT}/outputs/{SCENARIO}/base_detector_data.csv')

if __name__ == '__main__':
    setup_simulation()
    run_main_simulation()
    post_process_results()