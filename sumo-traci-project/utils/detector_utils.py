import xml.etree.ElementTree as ET
import traci
import csv, os

def get_edge_ids_from_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    incidents_data = {} # {incident_id: [(edge_id, distance), ...], ...}
    for incident in root.findall('Incident'):
        incident_id = incident.get('id')
        edges = [(edge.get('id'), float(edge.get('distance'))) for edge in incident.findall('Edge')]
        incidents_data[incident_id] = edges
        print(incidents_data)
    return incidents_data

def calculate_detector_positions(net, incidents_data, interval):
    detectors = {}
    for incident_id, edges in incidents_data.items():
        # Initialize a list to hold detector positions for the incident edge
        incident_edge, incident_distance = edges[0]
        incident_edge_length = net.getEdge(incident_edge).getLength()
        incident_edge_detectors = []

        # Place a detector at the incident location
        incident_position = incident_edge_length - incident_distance
        incident_edge_detectors.append(incident_position)

        # Place additional detectors upstream from the incident
        position = incident_position - interval
        while position > 0:
            incident_edge_detectors.append(position)
            position -= interval
        detectors[incident_edge] = incident_edge_detectors

        # Process the upstream edges
        for edge_id, _ in edges[1:]:
            edge_length = net.getEdge(edge_id).getLength()
            positions = []
            # Start placing detectors from the end of the edge towards the connection
            position = edge_length - interval
            while position > 0:
                positions.append(position)
                position -= interval
            detectors[edge_id] = positions

    print(detectors)
    return detectors

def calculate_detector_positions1(net, incidents_data, interval):
    detectors = {}
    for incident_id, edges in incidents_data.items():
        for edge_id, distance in edges:
            edge_length = net.getEdge(edge_id).getLength()
            start_position = edge_length - distance  # Start from the incident location
            positions = [start_position]
            while positions[-1] + interval < edge_length:
                positions.append(positions[-1] + interval)
            detectors[f"{incident_id}_{edge_id}"] = positions
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

            # Calculate flow, density, and average speed
            flow, density, avg_speed = calculate_traffic_parameters(speeds)

            # Create a unique detector key for storing data
            detector_key = f"{edge_id}_{pos}"
            store_detector_data(accumulated_data, detector_key, current_time, flow, density, avg_speed)

def calculate_traffic_parameters(speeds):
    flow = len(speeds) * 3600 / traci.simulation.getDeltaT()
    density = len(speeds) / 0.1  # Assuming lane width of 0.1
    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    return flow, density, avg_speed

def store_detector_data(accumulated_data, detector_key, current_time, flow, density, avg_speed):
    if detector_key not in accumulated_data:
        accumulated_data[detector_key] = []
    accumulated_data[detector_key].append({
        "time": current_time,
        "flow": flow,
        "density": density,
        "average_speed": avg_speed
    })

def simulate_detectors1(detectors, accumulated_data, current_time):
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

def save_detectors_to_xml1(detectors, scenario, project):
    root = ET.Element("Detectors")

    for detector_key, positions in detectors.items():
        edge_id, incident_id = detector_key.split('_')
        for pos in positions:
            detector_elem = ET.SubElement(root, "Detector", edge=edge_id, position=str(pos), incident=incident_id)

    file_name = f'data/{project}/outputs/{scenario}/upstream_detectors.xml'
    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    tree.write(file_name)

def save_detectors_to_xml(detectors, scenario, project):
    root = ET.Element("Detectors")

    for detector_key, positions in detectors.items():
        parts = detector_key.split('_')
        edge_id = '_'.join(parts[:-1])  # Join all parts except the last one
        incident_id = parts[-1]  # The last part is the incident_id
        for pos in positions:
            detector_elem = ET.SubElement(root, "Detector", edge=edge_id, position=str(pos), incident=incident_id)

    file_name = f'data/{project}/outputs/{scenario}/detectors.xml'
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    tree = ET.ElementTree(root)
    tree.write(file_name)

