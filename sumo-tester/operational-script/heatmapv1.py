import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load the CSV file
file_path = "ratios_results.csv" 
data = pd.read_csv(file_path)

# Create a pivot table for SPR and FR based on Edge (x-axis) and Time (y-axis)
spr_matrix = data.pivot(index="time", columns="edge", values="SPR")
fr_matrix = data.pivot(index="time", columns="edge", values="FR")

# Replace NaN or Inf values with 1.0 (default to "Negligible" condition)
spr_matrix = spr_matrix.replace([np.inf, -np.inf], np.nan).fillna(1.0)
fr_matrix = fr_matrix.replace([np.inf, -np.inf], np.nan).fillna(1.0)

# Cap values to the upper bound of 1
spr_matrix = spr_matrix.clip(upper=1.0)
fr_matrix = fr_matrix.clip(upper=1.0)

# Define the range for data to include in the heatmap
x_start = "E1_0m"      # Start distance (inclusive)
x_end = "E1_2500m"     # End distance (inclusive)
y_start = 401.3        # Start time (inclusive)
y_end = 2801.3         # End time (inclusive)

# Filter rows (y-axis) based on time range
spr_matrix = spr_matrix.loc[y_start:y_end]
fr_matrix = fr_matrix.loc[y_start:y_end]

# Filter columns (x-axis) by extracting numeric values from distance labels
def filter_columns(matrix, x_start, x_end):
    numeric_start = int(x_start.split('_')[1][:-1])
    numeric_end = int(x_end.split('_')[1][:-1])
    sorted_columns = sorted(matrix.columns, key=lambda x: int(x.split('_')[1][:-1]))
    filtered_columns = [col for col in sorted_columns if numeric_start <= int(col.split('_')[1][:-1]) <= numeric_end]
    return matrix[filtered_columns]

spr_matrix = filter_columns(spr_matrix, x_start, x_end)
fr_matrix = filter_columns(fr_matrix, x_start, x_end)

# Calculate the mean for SPR and FR within the specified range
spr_mean = spr_matrix.mean().mean()
fr_mean = fr_matrix.mean().mean()

# Define the colour-coding scheme for the heatmap
def get_colour_map():
    from matplotlib.colors import ListedColormap, BoundaryNorm
    colours = ["red", "orange", "yellow", "green"]  # Severe, Major, Moderate, Negligible
    bounds = [0.0, 0.25, 0.50, 0.75, 1.0]  # Cap at 1
    cmap = ListedColormap(colours)
    norm = BoundaryNorm(bounds, cmap.N)
    return cmap, norm

# Replace values greater than 1 with ">1" for display purposes
spr_display_matrix = spr_matrix.copy()
fr_display_matrix = fr_matrix.copy()

# Replace capped values for display
spr_display_matrix[spr_matrix >= 1.0] = np.nan  # Temporarily replace for mixed annotations
fr_display_matrix[fr_matrix >= 1.0] = np.nan

# Adjust the data to show ">1" where applicable
def update_display_matrix(matrix, original_matrix):
    display_matrix = matrix.astype(str)
    display_matrix[original_matrix >= 1.0] = ">1"
    return display_matrix

spr_display_matrix = update_display_matrix(spr_display_matrix, spr_matrix)
fr_display_matrix = update_display_matrix(fr_display_matrix, fr_matrix)

# Normalise time to start from 0 and create interval labels
time_intervals = spr_matrix.index - spr_matrix.index.min()
print(time_intervals)
interval_labels = [f"{int(start)}-{int(start + 300)}" for start in time_intervals]

# Plot heatmap for a given matrix
def plot_heatmap(matrix, display_matrix, title, data_mean, interval_labels):
    cmap, norm = get_colour_map()
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        matrix,
        cmap=cmap,
        norm=norm,
        annot=display_matrix,
        fmt="",
        cbar=True,
        cbar_kws={"label": "Operational Impact Rating"},
        annot_kws={"rotation": 90},
    )
    plt.title(title)
    plt.xlabel("Distance (m)")
    plt.ylabel("Time Intervals (s)")

    # Set the y-axis labels to the time intervals
    plt.yticks(ticks=np.arange(len(interval_labels)) + 0.5, labels=interval_labels, rotation=0)

    # Add the mean value to the top-left corner of the plot
    plt.text(
        x=-0.5, y=-0.5,
        s=f"SOI: {data_mean:.3f}",
        fontsize=12, color="black", fontweight="bold",
    )

    plt.xticks(rotation=90)
    plt.show()

# Plot SPR heatmap
plot_heatmap(spr_matrix, spr_display_matrix, "SPR Heatmap", spr_mean, interval_labels)

# Plot FR heatmap
plot_heatmap(fr_matrix, fr_display_matrix, "FR Heatmap", fr_mean, interval_labels)