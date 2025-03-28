import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

def clean_and_prepare_csv(file_path):
    # Load the CSV file and clean it
    data = pd.read_csv(file_path, skiprows=1)
    # Rename columns for clarity
    data.columns = [
        "time", "timeduration", "to", 
        "car_from_52783895_to_682745311", "HGV_from_52783895_to_682745311",
        "car_from_4241669_to_682745311", "HGV_from_4241669_to_682745311"
    ]
    return data

def generate_auto_routed_xml(data, output_file="routes_fixed.rou.xml"):
    # Create the root element for the XML
    root = ET.Element("routes")

    # Define vehicle types
    ET.SubElement(root, "vType", id="car", vClass="passenger", lcKeepRight="0.9", color="yellow")
    ET.SubElement(root, "vType", id="HGV", vClass="truck", maxSpeed="31.0", accel="1.3", decel="3.5",
                  lcStrategic="0.2", lcCooperative="0.5", lcKeepRight="1.0", color="red")

    # Process each row to create flows
    for _, row in data.iterrows():
        # Handle non-header rows (ensure correct numeric types)
        try:
            start_time = int(row["time"])
            duration = int(row["timeduration"])
            end_time = start_time + duration

            for col in data.columns[3:]:
                if "_" in col:
                    vehicle_type, from_node, to_node = col.split("_")[0], col.split("_")[2], col.split("_")[4]
                    flow_count = int(row[col])

                    if flow_count > 0:  # Only add flows with non-zero count
                        flow_attributes = {
                            "id": f"flow_{from_node}_to_{to_node}_{vehicle_type}_{start_time}",
                            "type": vehicle_type,
                            "begin": str(start_time),
                            "end": str(end_time),
                            "number": str(flow_count),
                            "from": from_node,
                            "to": to_node,
                            "departSpeed": "avg",  # Default for all flows
                        }

                        # Add specific attributes for car flows
                        if vehicle_type == "car":
                            flow_attributes["departLane"] = "free"

                        # Create the flow element with attributes
                        ET.SubElement(root, "flow", attrib=flow_attributes)
        except ValueError:
            # Skip rows where conversion to int fails (likely header rows)
            continue

    # Beautify and write XML
    xml_string = ET.tostring(root, encoding="unicode")
    pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")

    with open(output_file, "w") as f:
        f.write(pretty_xml)

    print(f"{output_file} has been created with auto-routing enabled!")

if __name__ == "__main__":
    # Set the path to your CSV file
    csv_file_path = "M25.csv"  # Replace with your actual file name
    cleaned_data = clean_and_prepare_csv(csv_file_path)
    generate_auto_routed_xml(cleaned_data)
