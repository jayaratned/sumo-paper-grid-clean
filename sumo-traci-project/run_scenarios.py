import configparser
import subprocess
import time
import shutil
import os

def run_simulation(config):
    # Update the 'config.ini' file with new settings
    config_file_path = 'config.ini'
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

    # Debug: Read it back
    config_read = configparser.ConfigParser()
    config_read.read(config_file_path)
    print("Sections in config file after writing:", config_read.sections())

    # Call main.py here to run the simulation
    main_py_path = 'main.py'  # Update this path if main.py is not in the same directory
    if not os.path.exists(main_py_path):
        print(f"Error: {main_py_path} does not exist.")
        return

    start_time = time.time()
    subprocess.run(['python', main_py_path])
    end_time = time.time()
    print(f"Scenario time taken: {end_time - start_time} seconds")

def save_config_file(config_file_path, output_dir):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define the destination path for the config file
    destination_path = os.path.join(output_dir, 'config.ini')

    # Use shutil to copy the file
    shutil.copy(config_file_path, destination_path)
    print(f"Config file saved to: {destination_path}")

if __name__ == '__main__':
    start_total_time = time.time()
    print("Starting simulation counter...")

    # Read the original config file
    config_file_path = 'config.ini'
    if not os.path.exists(config_file_path):
        print(f"Error: {config_file_path} does not exist.")
        exit(1)

    config = configparser.ConfigParser()
    config.read(config_file_path)
    print(f"Sections available: {config.sections()}")

    # Scenarios to be run
    scenarios = [
        {'Edge_Detection': 'True', 'ego_Breakdown_Enabled': 'True'},
        {'Edge_Detection': 'False', 'ego_Breakdown_Enabled': 'False'},
        {'Edge_Detection': 'False', 'ego_Breakdown_Enabled': 'True'},
    ]

    for scenario in scenarios:
        # Modify the config values
        config['Simulation']['Edge_Detection'] = scenario['Edge_Detection']
        config['Simulation']['ego_Breakdown_Enabled'] = scenario['ego_Breakdown_Enabled']

        # Run the simulation
        run_simulation(config)

    end_total_time = time.time()
    print(f"Total time for all simulations: {end_total_time - start_total_time} seconds")

    # # Save the config file to the output directory
    # project = config['Files']['Project']
    # scenario = config['Simulation']['Scenario']
    # output_dir = f'data/{project}/outputs/{scenario}'

    # save_config_file(config_file_path, output_dir)
