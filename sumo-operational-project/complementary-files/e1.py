# Generate e1 detector file for 100m intervals on a 6km road
road_length = 5000  # 6 km in meters
interval = 100  # Detector interval in meters
lane_ids = ["E0_0", "E0_1"]  # Replace with your actual lane IDs

with open("e1detectors.add.xml", "w") as f:
    f.write('<additional>\n')
    detector_id = 0
    for pos in range(0, road_length + 1, interval):
        for lane in lane_ids:
            f.write(f'    <e1Detector id="{lane}_{pos}m" lane="{lane}" pos="{pos}" period="300" file="e1/test.xml"/>\n')
            # f.write(f'    <e1Detector id="{lane}_{pos}m" lane="{lane}" pos="{pos}"/>\n')
            detector_id += 1
    f.write('</additional>')
