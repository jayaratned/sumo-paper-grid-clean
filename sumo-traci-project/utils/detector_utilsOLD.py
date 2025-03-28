import xml.etree.ElementTree as ET
import traci
import csv

def get_edge_ids_from_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    edge_ids = [edge.get('id') for edge in root.findall('Edge')]
    return edge_ids

def calculate_detector_positions(net, edge_ids, start_position, interval):
    detectors = {}
    for edge_id in edge_ids:
        edge_length = net.getEdge(edge_id).getLength()
        positions = [start_position]
        while positions[-1] + interval < edge_length:
            positions.append(positions[-1] + interval)
        detectors[edge_id] = positions
    return detectors

def simulate_detectors(detectors, accumulated_data, current_time):
    for edge_id, positions in detectors.items():
        for pos in positions:
            speeds = []
            vehicle_ids = traci.edge.getLastStepVehicleIDs(edge_id)
            for vehicle_id in vehicle_ids:
                vehicle_pos = traci.vehicle.getLanePosition(vehicle_id)
                vehicle_speed = traci.vehicle.getSpeed(vehicle_id)
                if pos - 50 <= vehicle_pos <= pos + 50:
                    speeds.append(vehicle_speed)

            flow = len(speeds) * 3600 / traci.simulation.getDeltaT()
            density = len(speeds) / 0.1
            avg_speed = sum(speeds) / len(speeds) if speeds else 0

            detector_key = f"{edge_id}_{pos}"
            if detector_key not in accumulated_data:
                accumulated_data[detector_key] = []
            accumulated_data[detector_key].append({
                "time": current_time,
                "flow": flow,
                "density": density,
                "average_speed": avg_speed
            })

def write_detector_data_to_csv(accumulated_data, filename):
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['detector', 'time', 'flow', 'density', 'average_speed']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for detector, data in accumulated_data.items():
            for record in data:
                writer.writerow({
                    'detector': detector,
                    'time': record['time'],
                    'flow': record['flow'],
                    'density': record['density'],
                    'average_speed': record['average_speed']
                })

