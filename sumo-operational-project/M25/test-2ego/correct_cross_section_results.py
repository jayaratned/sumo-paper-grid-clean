import pandas as pd

# Load the CSV file
file_path = "cross_section_results.csv"  # Update this if your file has a different name
df = pd.read_csv(file_path)

# Create a copy of the original dataframe to track changes
df_fixed = df.copy()

# Identify the columns that need fixing (only numeric columns)
columns_to_fix = ["mean_speed", "flowrate", "SPI"]

# Store changes for reference
changes = []

# Iterate over the dataframe and replace negative values with the next row's value
for col in columns_to_fix:
    for i in range(len(df) - 1):  # Avoid last row as there is no next row to take values from
        if df_fixed.at[i, col] < 0:
            new_value = df_fixed.at[i + 1, col]  # Use next row's value
            changes.append({
                "time": df_fixed.at[i, "time"],
                "edge": df_fixed.at[i, "edge"],
                "column": col,
                "old_value": df_fixed.at[i, col],
                "new_value": new_value
            })
            df_fixed.at[i, col] = new_value

# Save the corrected dataframe
output_file = "fixed_data.csv"
df_fixed.to_csv(output_file, index=False)

# Save the log of changes
changes_df = pd.DataFrame(changes)
changes_df.to_csv("changes_log.csv", index=False)

print(f"Fixed data saved as {output_file}")
print(f"Log of changes saved as changes_log.csv")
