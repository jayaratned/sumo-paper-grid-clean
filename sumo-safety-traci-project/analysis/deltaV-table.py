import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Define the logistic function to calculate probability for each MAIS level
def calculate_probability(coeff, delta_v):
    return np.exp(coeff[0] + coeff[1] * delta_v) / (1 + np.exp(coeff[0] + coeff[1] * delta_v))

# Coefficients for each MAIS level for frontal and rear-end crashes
coefficients_frontal = {
    'MAIS 1+': (-1.4930, 0.0854),
    'MAIS 2+': (-4.9429, 0.1425),
    'MAIS 3+': (-6.9774, 0.1620),
    'MAIS 4+': (-8.4254, 0.1586),
    'MAIS 5+': (-8.8355, 0.1566),
    'Fatality': (-9.0422, 0.1571)
}

coefficients_rear = {
    'MAIS 1+': (-1.8199, 0.0671),
    'MAIS 2+': (-6.1818, 0.1482),
    'MAIS 3+': (-8.0329, 0.1793),
    'MAIS 4+': (-11.8787, 0.2210),
    'MAIS 5+': (-12.1944, 0.2276),
    'Fatality': (-12.1982, 0.2255)
}

# Function to calculate probabilities for frontal and rear-end crashes
def calculate_probabilities(delta_v):
    probabilities_frontal = {level: calculate_probability(coeff, delta_v) for level, coeff in coefficients_frontal.items()}
    probabilities_rear = {level: calculate_probability(coeff, delta_v) for level, coeff in coefficients_rear.items()}

    probabilities_frontal['MAIS 0'] = 1 - probabilities_frontal['MAIS 1+']
    probabilities_rear['MAIS 0'] = 1 - probabilities_rear['MAIS 1+']

    return probabilities_frontal, probabilities_rear

# Calculate S0 to S3 for both frontal and rear-end crashes
def calculate_simplified_probabilities(probabilities):
    s0 = probabilities['MAIS 0']
    s1 = probabilities['MAIS 1+']
    s2 = probabilities['MAIS 3+']
    s3 = probabilities['MAIS 5+']

    return [s0, s1, s2, s3]

# Collect data for delta_v from 0 to 40
data = []

for delta_v in range(81):
    probabilities_frontal, probabilities_rear = calculate_probabilities(delta_v)
    simplified_frontal = calculate_simplified_probabilities(probabilities_frontal)
    simplified_rear = calculate_simplified_probabilities(probabilities_rear)
    
    data.append({
        'Delta_V': delta_v,
        'Frontal_MAIS_0': probabilities_frontal['MAIS 0'],
        'Frontal_MAIS_1+': probabilities_frontal['MAIS 1+'],
        'Frontal_MAIS_2+': probabilities_frontal['MAIS 2+'],
        'Frontal_MAIS_3+': probabilities_frontal['MAIS 3+'],
        'Frontal_MAIS_4+': probabilities_frontal['MAIS 4+'],
        'Frontal_MAIS_5+': probabilities_frontal['MAIS 5+'],
        'Frontal_Fatality': probabilities_frontal['Fatality'],
        'Frontal_S0': simplified_frontal[0],
        'Frontal_S1': simplified_frontal[1],
        'Frontal_S2': simplified_frontal[2],
        'Frontal_S3': simplified_frontal[3],
        'Rear_MAIS_0': probabilities_rear['MAIS 0'],
        'Rear_MAIS_1+': probabilities_rear['MAIS 1+'],
        'Rear_MAIS_2+': probabilities_rear['MAIS 2+'],
        'Rear_MAIS_3+': probabilities_rear['MAIS 3+'],
        'Rear_MAIS_4+': probabilities_rear['MAIS 4+'],
        'Rear_MAIS_5+': probabilities_rear['MAIS 5+'],
        'Rear_Fatality': probabilities_rear['Fatality'],
        'Rear_S0': simplified_rear[0],
        'Rear_S1': simplified_rear[1],
        'Rear_S2': simplified_rear[2],
        'Rear_S3': simplified_rear[3]
    })

# Convert data to DataFrame
df = pd.DataFrame(data)

# Save DataFrame to CSV
csv_file = "crash_probabilities.csv"
df.to_csv(csv_file, index=False)

import ace_tools as tools; tools.display_dataframe_to_user(name="Crash Probabilities Data", dataframe=df)
