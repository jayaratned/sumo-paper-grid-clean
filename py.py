import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV file into a DataFrame
df = pd.read_csv('combined_cve_data.csv')

# Extract the year from the 'CVE ID' column and create a new 'Year' column
df['Year'] = df['CVE ID'].str.extract(r'(\d{4})')

# Group by 'Year' and count the number of vulnerabilities for each year
yearly_vulnerability_count = df['Year'].value_counts().sort_index()

# Display the yearly vulnerability count
print(yearly_vulnerability_count)

# Plot the yearly vulnerability count except for the current year 2024
yearly_vulnerability_count[:-1].plot(kind='bar', xlabel='Year', ylabel='Number of Vulnerabilities', title='Yearly Vulnerability Count')

# View the plot
plt.show()

# Save the plot as a PNG file
plt.savefig('yearly_vulnerability_count.png')