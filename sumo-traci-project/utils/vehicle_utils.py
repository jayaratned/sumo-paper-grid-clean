import traci
import os
import subprocess
import csv
import math
import sumolib
import sys
import pandas as pd
import xml.etree.ElementTree as ET

issued_slowdown = {}  # Dictionary to track vehicles for which slowdown was issued and their timestamp
vehicle_stop_data = []  # Global list to store data about stopped vehicles

# stop and save ego data to file
def stop_all_egos_at_current_position(stop_time, stop_duration, ego_type):
    """
    At a given simulation time, slows down all vehicles of type 'ego' 
    and then stops them at their current position for a specified duration.
    
    Args:
    - stop_time (int): The simulation time step at which to slow down the vehicles.
    - stop_duration (int): The duration for which the vehicles should remain stopped after they've come to a halt.
    - issued_slowdown (dict): A dictionary to track vehicles for which slowdown was issued and their timestamp.
    
    Returns:
    - dict: Updated issued_slowdown dictionary.
    """
    
    current_time = traci.simulation.getTime()
    DECELERATION_RATE = 4.5 # m/s^2

    if current_time == stop_time:
        for vehicle_id in traci.vehicle.getIDList():
            if traci.vehicle.getTypeID(vehicle_id) == ego_type:
                current_speed = traci.vehicle.getSpeed(vehicle_id)
                time_to_stop = math.ceil(current_speed / DECELERATION_RATE) 
                traci.vehicle.slowDown(vehicle_id, 0, time_to_stop)
                issued_slowdown[vehicle_id] = current_time

    for vehicle_id in list(issued_slowdown.keys()):
        if traci.vehicle.getSpeed(vehicle_id) == 0:
            position = traci.vehicle.getPosition(vehicle_id)
            lane_id = traci.vehicle.getLaneID(vehicle_id)
            edge_id = traci.vehicle.getRoadID(vehicle_id)
            position_on_lane = traci.vehicle.getLanePosition(vehicle_id)
            
            stop_data = {
                'vehicle_id': vehicle_id,
                'slowdown_issued': issued_slowdown[vehicle_id],
                'actual_stop_time': current_time,
                'position': position,
                'lane_id': lane_id,
                'edge_id': edge_id,
                'position_on_lane': position_on_lane
            }
            vehicle_stop_data.append(stop_data)
            traci.vehicle.setStop(vehicle_id, edge_id, traci.vehicle.getLanePosition(vehicle_id), duration=stop_duration, laneIndex=0, flags=0)
            del issued_slowdown[vehicle_id]

    return issued_slowdown
def write_stopped_vehicles_to_file(scenario, project):
    """
    Writes the accumulated data of stopped vehicles to a file.
    
    Parameters:
    - scenario: The scenario for the simulation.
    - project: The project name.
    - vehicle_stop_data: Data of stopped vehicles.
    
    Returns:
    - str: The full path to the created file.
    """
    output_path = f'data/{project}/outputs/{scenario}/stopped_vehicles.csv'
    directory = os.path.dirname(output_path)
    os.makedirs(directory, exist_ok=True)
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['vehicle_id', 'slowdown_issued', 'actual_stop_time', 'position_x', 'position_y', 'lane_id', 'edge_id', 'position_on_lane'])
        writer.writeheader()

        for data in vehicle_stop_data:
            writer.writerow({
                'vehicle_id': data['vehicle_id'],
                'slowdown_issued': data['slowdown_issued'],
                'actual_stop_time': data['actual_stop_time'],
                'position_x': data['position'][0],
                'position_y': data['position'][1],
                'lane_id': data['lane_id'],
                'edge_id': data['edge_id'],
                'position_on_lane': data['position_on_lane']
            })
    
    return output_path
# Supporting function for get_edges_near_stopped_egos - works only for fivebyfive scenario
def get_opposite_edge(edge):
    """Returns the opposite edge given the naming convention.
        only works for fivebyfive scenario!
    """
    return edge[2:] + edge[:2]
# Get edges within specified radius stopped egos - needs improvement!
def get_edges_near_stopped_egos(radius, ego_type):
    """
    This function gets first lane on an edge ("_0") and checks if the distance between the stopped ego 
    and the lane is less than the radius. The coordinates returned are the coordinates of the lane centre 
    line starting point and ending point. The function checks if either end of the lane is within the radius.
    The edge cases that are not captured are:
     - if the ego is stopped on midway on a lane and the radius is less than half of the lane length
       in close proximity to the ego, then the lane will not be captured. This would typically be the 
       opposite lane of the ego. (this is issue is rectified for fivebyfive scenario through
       get opposite edge function, but not for other scenarios since the opposite edge is not known)
    
    Returns all edges within a given radius of all stopped egos.
    
    Args:
    - radius (float): The distance radius to consider.
    
    Returns:
    - set: A set of nearby edges.
    """
    nearby_edges = set()
    
    for vehicle_id in traci.vehicle.getIDList():
        if traci.vehicle.getTypeID(vehicle_id) == ego_type and traci.vehicle.isStopped(vehicle_id):
            
            # Add the current edge of the stopped ego to the set
            current_edge = traci.vehicle.getRoadID(vehicle_id)
            nearby_edges.add(current_edge)
            
            # Add the opposite edge of the stopped ego to the set
            opposite_edge = get_opposite_edge(current_edge)
            nearby_edges.add(opposite_edge)
            
            position = traci.vehicle.getPosition(vehicle_id)
            x, y = position
            # print (f"Vehicle {vehicle_id} is stopped at position ({x}, {y})")
            for edge in traci.edge.getIDList():
                if edge[0] != ':':
                    for lane_pos in traci.lane.getShape(edge + "_0"):
                        # print(f"lane_pos = {lane_pos}")
                        distance = ((x - lane_pos[0])**2 + (y - lane_pos[1])**2)**0.5
                        # print(f"x = {lane_pos[0]}, y = {lane_pos[1]}")
                        if distance <= radius:
                            nearby_edges.add(edge)
                                                  
    return nearby_edges
def save_radius_edges_as_xml(nearby_edges, scenario, project):
    root = ET.Element("RadiusEdges")

    for edge_id in nearby_edges:
        ET.SubElement(root, "Edge", id=edge_id)

    file_name = f'data/{project}/outputs/{scenario}/radius_edges.xml'
    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    tree.write(file_name)

# Incidents on internal edges are handled and included - incidents are saved seperately - previous working version
# def get_upstream_edges_with_distance(file_path, net, distance_limit, partial_inclusion):
#     df = pd.read_csv(file_path)

#     all_incidents_upstream_edges = {}

#     for _, row in df.iterrows():
#         incident_id = row['vehicle_id']
#         edge_id = row['edge_id']
#         position_on_lane = row['position_on_lane']

#         visited_edges = set([edge_id])

#         # Handle internal edges
#         if edge_id.startswith(':'):
#             internal_edge = net.getEdge(edge_id)
#             print("internal_edge:", internal_edge)
#             if internal_edge:
#                 from_node = internal_edge.getFromNode()
#                 print("from_node:", from_node)
#                 incoming_edges = [e for e in from_node.getIncoming() if e.getID() not in visited_edges]
#                 # print(incoming_edges)
#                 if incoming_edges:
#                     edge_id = incoming_edges[0].getID()
#                     print("edge_id:", edge_id)
#                     position_on_lane = incoming_edges[0].getLength()
#                     print("position_on_lane:", position_on_lane)
#                 else:
#                     print(f"No incoming edges found for internal edge {edge_id}")
#                     continue

#         all_upstream_edges = {edge_id: position_on_lane}
#         queue = [(edge_id, position_on_lane)]
#         print("queue:", queue)

#         while queue:
#             current_edge_id, distance_from_incident = queue.pop(0)
#             current_edge = net.getEdge(current_edge_id)
#             print("current_edge:", current_edge)
#             current_from_node = current_edge.getFromNode()
#             print("current_from_node:", current_from_node)
#             current_to_node = current_edge.getToNode()
#             print("current_to_node:", current_to_node)

#             if distance_from_incident < distance_limit:
#                 for incoming_edge in current_from_node.getIncoming():
#                     incoming_edge_id = incoming_edge.getID()
#                     incoming_edge_from_node = incoming_edge.getFromNode()
#                     print("incoming_edge_id:", incoming_edge_id, "incoming_edge_from_node:", incoming_edge_from_node)

#                     if (incoming_edge_id not in visited_edges 
#                         and not incoming_edge_id.startswith(':') 
#                         and incoming_edge_from_node != current_to_node):
                        
#                         visited_edges.add(incoming_edge_id)
#                         new_distance_from_incident = distance_from_incident + incoming_edge.getLength()
#                         print("vipartial_edge_inclusion = Truesited_edges:", visited_edges)

#                         if partial_inclusion:
#                             # Add edge if any part of it is within the distance limit
#                             if new_distance_from_incident - incoming_edge.getLength() < distance_limit:
#                                 all_upstream_edges[incoming_edge_id] = new_distance_from_incident
#                                 print("all_upstream_edges:", all_upstream_edges)
#                         else:
#                             # Add edge only if its end is within the distance limit
#                             if new_distance_from_incident <= distance_limit:
#                                 all_upstream_edges[incoming_edge_id] = new_distance_from_incident

#                         if new_distance_from_incident <= distance_limit:
#                             queue.append((incoming_edge_id, new_distance_from_incident))
#                             print("queue:", queue)

#         all_incidents_upstream_edges[incident_id] = all_upstream_edges
#         print("all_incidents_upstream_edges:", all_incidents_upstream_edges)

#     return all_incidents_upstream_edges

# Updated by removing unnecessary internal edge handling - current working version
def get_upstream_edges_with_distance(file_path, net, distance_limit, partial_inclusion):
    df = pd.read_csv(file_path)

    all_incidents_upstream_edges = {}
    all_incidents_edge_tags = {}  # Dictionary to store edge tags

    for _, row in df.iterrows():
        incident_id = row['vehicle_id']
        edge_id = row['edge_id']
        position_on_lane = row['position_on_lane']
        print(edge_id, position_on_lane)

        visited_edges = set([edge_id])

        all_upstream_edges = {edge_id: position_on_lane}
        all_edge_tags = {edge_id: "0"}  # Tagging the incident edge as level 0
        queue = [(edge_id, position_on_lane, "0")]  # Adding initial depth tag
        print("queue:", queue)

        while queue:
            current_edge_id, distance_from_incident, current_tag = queue.pop(0)
            current_edge = net.getEdge(current_edge_id)
            print("current_edge:", current_edge)
            current_from_node = current_edge.getFromNode()
            print("current_from_node:", current_from_node)
            current_to_node = current_edge.getToNode()
            print("current_to_node:", current_to_node)

            if distance_from_incident < distance_limit:
                sub_edge_count = 0  # Counter for edges at the same level
                for incoming_edge in current_from_node.getIncoming():
                    incoming_edge_id = incoming_edge.getID()
                    incoming_edge_from_node = incoming_edge.getFromNode()
                    print("incoming_edge_id:", incoming_edge_id, "incoming_edge_from_node:", incoming_edge_from_node)

                    if (incoming_edge_id not in visited_edges 
                        and not incoming_edge_id.startswith(':') 
                        and incoming_edge_from_node != current_to_node):
                        
                        visited_edges.add(incoming_edge_id)
                        new_tag = f"{current_tag}_{sub_edge_count}"
                        all_edge_tags[incoming_edge_id] = new_tag
                        sub_edge_count += 1
                        new_distance_from_incident = distance_from_incident + incoming_edge.getLength()
                        print("visited_edges:", visited_edges)

                        if partial_inclusion:
                            # Add edge if any part of it is within the distance limit
                            if new_distance_from_incident - incoming_edge.getLength() < distance_limit:
                                all_upstream_edges[incoming_edge_id] = new_distance_from_incident
                                print("all_upstream_edges:", all_upstream_edges)
                        else:
                            # Add edge only if its end is within the distance limit
                            if new_distance_from_incident <= distance_limit:
                                all_upstream_edges[incoming_edge_id] = new_distance_from_incident

                        if new_distance_from_incident <= distance_limit:
                            queue.append((incoming_edge_id, new_distance_from_incident, new_tag))
                            print("queue:", queue)

        all_incidents_upstream_edges[incident_id] = all_upstream_edges
        all_incidents_edge_tags[incident_id] = all_edge_tags
        print("all_incidents_upstream_edges:", all_incidents_upstream_edges)
        print("all_incidents_edge_tags:", all_incidents_edge_tags)

    return all_incidents_upstream_edges, all_incidents_edge_tags
def save_upstream_edges_as_xml(incidents_upstream_edges, scenario, project):
    root = ET.Element("Incidents")

    for incident_id, edges in incidents_upstream_edges.items():
        incident_elem = ET.SubElement(root, "Incident", id=incident_id)
        for edge_id, distance in edges.items():
            ET.SubElement(incident_elem, "Edge", id=edge_id, distance=str(distance))


    file_name = f'data/{project}/outputs/{scenario}/upstream_edges.xml'
    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    tree.write(file_name)
def save_upstream_edge_tags_as_xml(all_incidents_edge_tags, scenario, project):
    root = ET.Element("Incidents")

    for incident_id, edges in all_incidents_edge_tags.items():
        incident_elem = ET.SubElement(root, "Incident", id=incident_id)
        for edge_id, tag in edges.items():
            ET.SubElement(incident_elem, "Edge", id=edge_id, tag=str(tag))


    file_name = f'data/{project}/outputs/{scenario}/upstream_edge_tags.xml'
    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    tree.write(file_name)
