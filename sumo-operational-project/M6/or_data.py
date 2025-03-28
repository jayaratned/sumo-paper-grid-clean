import pandas as pd

# Input and output file paths
input_file = "cross_section_results.csv"  # Replace with your input CSV file
output_file = "ratios_results.csv"  # Output file for SPR and FR

def calculate_ratios(input_file, output_file):
    # Load the input CSV
    data = pd.read_csv(input_file)

    # Separate attack and base scenarios
    attack_data = data[data["scenario"] == "attack"]
    base_data = data[data["scenario"] == "base"]

    # Merge attack and base data for comparison
    merged_data = pd.merge(
        attack_data,
        base_data,
        on=["time", "edge", "lanes"],  # Merge on time, edge, and lanes
        suffixes=("_attack", "_base")
    )

    # Calculate SPR and FR
    merged_data["SPR"] = (merged_data["mean_speed_attack"] / merged_data["mean_speed_base"]).round(2)
    merged_data["FR"] = (merged_data["flowrate_attack"] / merged_data["flowrate_base"]).round(2)

    # Select and format output columns
    output_data = merged_data[[
        "time",
        "edge",
        "SPR",
        "FR",
        "mean_speed_attack",
        "mean_speed_base",
        "flowrate_attack",
        "flowrate_base"
    ]].round(2)  # Round all numeric columns to 2 decimal places

    # Save results to a new CSV file
    output_data.to_csv(output_file, index=False)
    print(f"SPR and FR calculations saved to '{output_file}'.")

# Run the calculation
calculate_ratios(input_file, output_file)