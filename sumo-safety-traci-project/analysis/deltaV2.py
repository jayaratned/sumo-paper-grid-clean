import numpy as np
import matplotlib.pyplot as plt

# Increase base font size by 50%
plt.rcParams.update({'font.size': plt.rcParams['font.size'] * 1.5})

# Logistic function
def calculate_probability(coeff, delta_v):
    x = coeff[0] + coeff[1] * delta_v
    ex = np.exp(x)
    return ex / (1 + ex)

# Coefficients for each MAIS level (frontal & rear-end)
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

# Calculate MAIS probabilities for a given Delta-V
def calculate_probabilities(delta_v):
    pf = {lvl: calculate_probability(coeff, delta_v) for lvl, coeff in coefficients_frontal.items()}
    pr = {lvl: calculate_probability(coeff, delta_v) for lvl, coeff in coefficients_rear.items()}
    pf['MAIS 0'] = 1 - pf['MAIS 1+']
    pr['MAIS 0'] = 1 - pr['MAIS 1+']
    return pf, pr

# Simplify labels ("MAIS 1+" -> "1+", "MAIS 0" -> "0")
def simplify_labels(labels):
    return [lbl.replace("MAIS ", "").strip() for lbl in labels]

# ----- Plot MAIS distribution only -----
delta_v = 40  # mph
prob_f, prob_r = calculate_probabilities(delta_v)

categories = ['MAIS 0'] + list(coefficients_frontal.keys())
categories_simple = simplify_labels(categories)

frontal_values = [prob_f['MAIS 0']] + [prob_f[level] for level in coefficients_frontal.keys()]
rear_values = [prob_r['MAIS 0']] + [prob_r[level] for level in coefficients_rear.keys()]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Frontal
ax1.bar(categories_simple, frontal_values, color='blue', label='Frontal crashes')
ax1.set_xlabel('MAIS Level')
ax1.set_ylabel('Probability')
ax1.set_title(f'Frontal Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax1.set_ylim(0, 1)
for i, val in enumerate(frontal_values):
    ax1.text(i, val + 0.01, f'{val:.2f}', ha='center', va='bottom',
             fontsize=plt.rcParams['font.size'] * 0.9)

# Rear-end
ax2.bar(categories_simple, rear_values, color='red', label='Rear-end crashes')
ax2.set_xlabel('MAIS Level')
ax2.set_ylabel('Probability')
ax2.set_title(f'Rear-End Crash Injury Probabilities\nDelta-V = {delta_v} mph')
ax2.set_ylim(0, 1)
for i, val in enumerate(rear_values):
    ax2.text(i, val + 0.01, f'{val:.2f}', ha='center', va='bottom',
             fontsize=plt.rcParams['font.size'] * 0.9)

ax1.legend()
ax2.legend()
plt.tight_layout()
plt.savefig("mais_probabilities.pdf")
plt.close()
