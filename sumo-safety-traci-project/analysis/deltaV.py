import numpy as np
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

# Example: Calculate the probabilities for Delta V = 40 mph for frontal and rear-end crashes
delta_v = 0
probabilities_frontal, probabilities_rear = calculate_probabilities(delta_v)

# Adjust the order to put 'MAIS 0' as the first item
categories = ['MAIS 0'] + list(coefficients_frontal.keys())
frontal_values = [probabilities_frontal['MAIS 0']] + [probabilities_frontal[level] for level in coefficients_frontal.keys()]
rear_values = [probabilities_rear['MAIS 0']] + [probabilities_rear[level] for level in coefficients_rear.keys()]

# Create separate plots for frontal and rear-end crashes with subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Frontal crash probabilities bar chart
ax1.bar(categories, frontal_values, color='blue', label='Frontal Crashes')
ax1.set_xlabel('MAIS Level')
ax1.set_ylabel('Probability')
ax1.set_title(f'Frontal Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax1.set_ylim(0, 1)  # Set y-axis limits to probabilities range
for i, val in enumerate(frontal_values):
    ax1.text(i, val + 0.01, f'{val:.2f}', ha='center', va='bottom', fontsize=8)

# Rear-end crash probabilities bar chart
ax2.bar(categories, rear_values, color='red', label='Rear-End Crashes')
ax2.set_xlabel('MAIS Level')
ax2.set_ylabel('Probability')
ax2.set_title(f'Rear-End Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax2.set_title(f'Rear-End Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax2.set_ylim(0, 1)  # Set y-axis limits to probabilities range
for i, val in enumerate(rear_values):
    ax2.text(i, val + 0.01, f'{val:.2f}', ha='center', va='bottom', fontsize=8)

# Show legend and plot
ax1.legend()
ax2.legend()
plt.tight_layout()  # Adjust layout for better fit
plt.show()

# Calculate S0 to S3 for both frontal and rear-end crashes
def calculate_simplified_probabilities(probabilities):
    s0 = probabilities['MAIS 0']
    s1 = probabilities['MAIS 1+'] - probabilities['MAIS 2+']
    s2 = probabilities['MAIS 2+'] - probabilities['MAIS 4+']
    s3 = probabilities['MAIS 4+']
    return [s0, s1, s2, s3]

simplified_frontal = calculate_simplified_probabilities(probabilities_frontal)
simplified_rear = calculate_simplified_probabilities(probabilities_rear)

# Simplified categories for plotting
simplified_categories = ['S0', 'S1', 
                         'S2', 'S3']

# Plotting the simplified scales
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Frontal crash probabilities bar chart
ax1.bar(simplified_categories, simplified_frontal, color='blue', label='Frontal Crashes')
ax1.set_xlabel('Injury Severity')
ax1.set_ylabel('Probability')
ax1.set_title(f'ISO21434 mapped Frontal Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax1.set_ylim(0, 1)
for i, val in enumerate(simplified_frontal):
    ax1.text(i, val + 0.01, f'{val:.2f}', ha='center', va='bottom', fontsize=8)

# Rear-end crash probabilities bar chart
ax2.bar(simplified_categories, simplified_rear, color='red', label='Rear-End Crashes')
ax2.set_xlabel('Injury Severity')
ax2.set_ylabel('Probability')
ax2.set_title(f'ISO21434 mapped Rear-End Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax2.set_ylim(0, 1)
for i, val in enumerate(simplified_rear):
    ax2.text(i, val + 0.01, f'{val:.2f}', ha='center', va='bottom', fontsize=8)

# Show legend and plot
ax1.legend()
ax2.legend()
plt.tight_layout()
plt.show()
