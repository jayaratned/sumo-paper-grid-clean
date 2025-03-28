import xml.etree.ElementTree as ET
import pandas as pd
import xml.dom.minidom as minidom

# Load the CSV file
data = pd.read_csv("M6-daily.csv", skiprows=2)

# Rename columns for clarity
data.columns = [
    "time", "timeduration", "from", "car_25409515_385618477", "car_25409515_111657117",
    "car_3239957#1_385618477", "car_3239957#1_111657117", "HGV_25409515_385618477",
    "HGV_25409515_111657117", "HGV_3239957#1_385618477", "HGV_3239957#1_111657117"
]

def generate_auto_routed_xml(data, output_file="routes.rou.xml"):
    root = ET.Element("routes")

    # Define vehicle types
    ET.SubElement(root, "vType", id="car", vClass="passenger", lcKeepRight="0.9", color="yellow")
    ET.SubElement(root, "vType", id="HGV", vClass="truck", maxSpeed="31.0", accel="1.3", decel="3.5",
                  lcStrategic="0.2", lcCooperative="0.5", lcKeepRight="1.0", color="red")

    # Process each row to create flows
    for _, row in data.iterrows():
        start_time = int(row["time"])
        duration = int(row["timeduration"])
        end_time = start_time + duration

        for col in data.columns[3:]:
            if "_" in col:
                vehicle_type, from_node, to_node = col.split("_")
                flow_count = int(row[col])

                if flow_count > 0:  # Only add flows with non-zero count
                    ET.SubElement(
                        root,
                        "flow",
                        id=f"flow_{from_node}_to_{to_node}_{vehicle_type}_{start_time}",
                        type=vehicle_type,
                        begin=str(start_time),
                        end=str(end_time),
                        number=str(flow_count),
                        attrib={"from": from_node, "to": to_node},
                    )

    # Beautify and write XML
    xml_string = ET.tostring(root, encoding="unicode")
    pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")

    with open(output_file, "w") as f:
        f.write(pretty_xml)

    print(f"{output_file} has been created with auto-routing enabled!")

# Generate the route file
generate_auto_routed_xml(data)
