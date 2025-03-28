import traci
import os
import sys
import time
import shutil

# List of handler functions to be executed at every simulation step
observers = []

def register_observer(func):
    """Add a function to the observers list."""
    observers.append(func)

def unregister_observer(func):
    """Remove a function from the observers list."""
    observers.remove(func)

def clear_observers():
    """Clears all registered observer functions."""
    observers.clear()

def setup_sumo(sumo_gui, sumo_config_file): # this function needs to be refactored 
    try:
        sumo_home = os.environ['SUMO_HOME']
    except KeyError:
        sys.exit("Please declare environment variable 'SUMO_HOME'.")

    tools = os.path.join(sumo_home, 'tools')
    sys.path.append(tools)

    binary_name = 'sumo-gui' if sumo_gui else 'sumo'
    virtual_env = os.environ.get('VIRTUAL_ENV')

    if virtual_env:
        sumo_binary = os.path.join(virtual_env, 'bin', binary_name)
    else:
        sumo_binary = os.path.join("/home/don/.local/bin", binary_name)
        if not os.path.exists(sumo_binary):
            sys.exit(f"The SUMO binary was not found. Please set the 'SUMO_BINARY' environment variable or install SUMO.")

    traci.start([sumo_binary, "-c", sumo_config_file])

def run_simulation(simulation_end_time):
    """
    Runs a SUMO simulation until the specified end time is reached.

    Args:
        simulation_end_time (float): The time at which the simulation should end.

    Returns:
        None

    Example:
        >>> run_simulation(3600)
        Simulation runtime: 3600.123 seconds
    """
    start_time = time.time()  # Record the start time
    
    while traci.simulation.getTime() <= simulation_end_time:
        for observer in observers:
            observer()
        traci.simulationStep()

    end_time = time.time()  # Record the end time
    runtime = end_time - start_time  # Calculate the runtime

    print(f"\nSimulation runtime: {runtime:.3f} seconds")  # Output the runtime

    traci.close()

def save_config_file(config_file_path, output_dir):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define the destination path for the config file
    destination_path = os.path.join(output_dir, 'config.ini')

    # Use shutil to copy the file
    shutil.copy(config_file_path, destination_path)
    print(f"Config file saved to: {destination_path}")