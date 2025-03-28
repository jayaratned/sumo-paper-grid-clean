import traci

def main():
    traci.start(["sumo-gui", "-c", "M25.sumocfg"])
    while traci.simulation.getTime() < 3600:
        traci.simulationStep()

        x = traci.lanearea.getLastStepVehicleIDs("104359041_0_100m")
        y = traci.lanearea.getIntervalVehicleNumber("104359041_0_100m")

        print(f"Vehicle Number: {y}", f"Vehicle IDs: {x}")

    traci.close()

if __name__ == "__main__":
        main()