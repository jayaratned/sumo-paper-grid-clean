# Generate e1 detector file for 100m intervals on a 6km road
road_length = 3900  # 6 km in meters
interval = 100  # Detector interval in meters
lane_ids = ["104359041_0", "104359041_1", "104359041_2", "104359041_3"]   # Replace with your actual lane IDs

with open("lanedetectors.add.xml", "w") as f:
    f.write('<additional>\n')
    detector_id = 0
    for pos in range(0, road_length + 1, interval):
        for lane in lane_ids:
            f.write(f'    <laneAreaDetector id="{lane}_{pos}m" lane="{lane}" pos="{pos}" endPos="{pos+100}" file="NUL"/>\n')
            # f.write(f'    <e1Detector id="{lane}_{pos}m" lane="{lane}" pos="{pos}"/>\n')
            detector_id += 1
    f.write('</additional>')
