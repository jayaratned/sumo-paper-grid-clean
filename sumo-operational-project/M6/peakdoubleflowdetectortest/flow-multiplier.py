import xml.etree.ElementTree as ET

def modify_xml_numbers(file_path, output_path):
    # Parse the XML file
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Iterate through all 'flow' elements
    for flow in root.findall(".//flow"):
        # Get the 'number' attribute
        number = flow.get('number')
        if number:
            # Multiply the number by 2 and update the attribute
            new_number = int(number) * 2
            flow.set('number', str(new_number))
    
    # Write the modified XML back to a file
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)

# Usage
input_file = "routes.rou.xml"    # Path to your input XML file
output_file = "routes2.rou.xml"  # Path to save the modified XML file

modify_xml_numbers(input_file, output_file)
print(f"Modified XML saved to: {output_file}")
