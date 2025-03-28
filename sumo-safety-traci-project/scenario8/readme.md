Scenario 8

Four lane highway - 500m + 2000m + 500m 
Traffic density: low - mid - high
Speed limit: 120 km/h
Traffic modal split: 100% cars - 0% trucks, 80% cars - 20% trucks
Traffic composition: 100% human drivers
Driver behavior: normal (but with different quality of driving)
Road conditions: dry

Attack scenarios:

vehicle suddenly brakes
vehicle suddenly changes lane
vehicle suddenly accelerates
vehicle suddenly stops
vehicle suddenly changes lane and brakes
vehicle suddenly changes lane and accelerates
vehicle suddenly changes lane and stops

write seperate functions for each attack scenario above         


for flow:
define route
vtype distribution
define flow

python ../../env/lib/python3.10/site-packages/sumo/tools/createVehTypeDistribution.py vehconfig.txt
python ../../env/lib/python3.10/site-packages/sumo/tools/xml/xml2csv.py outputs.xml

python ../../env/lib/python3.10/site-packages/sumo/tools/xml/xml2csv.py
