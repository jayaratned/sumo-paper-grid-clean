import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import Normalize, LinearSegmentedColormap

# Define the range for data to include in the heatmap
x_start = "104359041_0m"      # Start distance (inclusive)
x_end = "104359041_3000m"     # End distance (inclusive)
y_start = 55029.5             # Start time (inclusive)
y_end = 58329.5               # End time (inclusive)

# Toggles
annot_toggle = True
selective_labels_toggle = False

# Load the CSV file
file_path = "ratios_resultsFix.csv" 
data = pd.read_csv(file_path)

# Adjust time values so the smallest becomes 0
min_time = data["time"].min()
data["adjusted_time"] = data["time"] - min_time

# Create a pivot table for SPR and FR based on Edge (x-axis) and Time (y-axis)
spr_matrix = data.pivot(index="adjusted_time", columns="edge", values="SPR")
fr_matrix = data.pivot(index="adjusted_time", columns="edge", values="FR")

# Replace NaN or Inf values with 1.0 (default to "Negligible" condition)
spr_matrix = spr_matrix.replace([np.inf, -np.inf], np.nan).fillna(1.0)
fr_matrix = fr_matrix.replace([np.inf, -np.inf], np.nan).fillna(1.0)

# Cap values to the upper bound of 1
spr_matrix = spr_matrix.clip(upper=1.0)
fr_matrix = fr_matrix.clip(upper=1.0)

# Adjust y_start and y_end based on the adjusted time
adjusted_y_start = y_start - min_time
adjusted_y_end = y_end - min_time

# Filter rows (y-axis) based on adjusted time range
spr_matrix = spr_matrix.loc[adjusted_y_start:adjusted_y_end]
fr_matrix = fr_matrix.loc[adjusted_y_start:adjusted_y_end]

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

# Define the gradient colour-coding scheme (Green for 1, Red for 0)
def get_fixed_gradient_colour_map():
    colours = ["red", "orange", "yellow", "green"]  # Gradient: Red (0) to Green (1)
    cmap = LinearSegmentedColormap.from_list("fixed_green_to_red", colours, N=256)
    norm = Normalize(vmin=0.0, vmax=1.0)  # Set the gradient range explicitly from 0 to 1
    return cmap, norm



# Function to generate interval labels and selectively display them
def generate_interval_labels(matrix, show_every_nth_label=5, selective_labels_toggle=False):
    time_intervals = matrix.index
    interval_labels = [
        f"[{int(round(start))},{int(round(end))})"
        for start, end in zip(
            time_intervals,
            list(time_intervals[1:]) + [time_intervals[-1] + (time_intervals[1] - time_intervals[0])]
        )
    ]

    if selective_labels_toggle:
        # Show only every nth label if the toggle is on
        y_ticks = np.arange(len(interval_labels))
        visible_ticks = y_ticks[::show_every_nth_label]  # Select every nth label
        visible_labels = [interval_labels[i] for i in visible_ticks]
        return visible_ticks, visible_labels

    # If toggle is off, show all labels
    y_ticks = np.arange(len(interval_labels))
    return y_ticks, interval_labels

# Plot heatmap with fixed gradient
def plot_fixed_gradient_heatmap(matrix, title, data_mean):
    cmap, norm = get_fixed_gradient_colour_map()
    plt.figure(figsize=(10, 7))  # Adjust figure size for similar layout
    ax = sns.heatmap(
        matrix,
        cmap=cmap,
        norm=norm,  # Apply fixed gradient normalization
        annot=matrix if annot_toggle else None,
        fmt=".2f" if annot_toggle else None,
        cbar=True,
        cbar_kws={"label": "Operational Impact Rating"},
        annot_kws={"fontsize": 8, "rotation": 45},  # Added rotation for annotation labels
    )
    cbar = ax.collections[0].colorbar
    cbar.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])  # Show only the thresholds
    cbar.set_ticklabels(["0.00", "0.25", "0.50", "0.75", "1.00"])

    # plt.title(title, fontsize=14, fontweight="bold", loc="center")  # Center-aligned bold title
    plt.xlabel("Distance (m)", fontsize=12)
    plt.ylabel("Time Intervals (s)", fontsize=12)

    # Generate y-axis interval labels with selective toggle
    y_ticks, interval_labels = generate_interval_labels(
        matrix, show_every_nth_label=5, selective_labels_toggle=selective_labels_toggle
    )

    # Set the y-axis labels
    plt.yticks(
        ticks=y_ticks + 0.5,  # Adjust ticks to align with heatmap rows
        labels=interval_labels,
        fontsize=10, rotation=0,
    )

    # Add the mean value to the top-left corner of the plot
    plt.text(
        x=-0.5, y=-0.5,
        s=f"SOI: {data_mean:.3f}",
        fontsize=10, color="black", fontweight="bold",
    )

    plt.xticks(fontsize=10, rotation=90)  # Match original x-axis formatting
    plt.tight_layout()  # Adjust layout to prevent clipping
    plt.show()

# Plot SPR heatmap with fixed gradient
plot_fixed_gradient_heatmap(spr_matrix, "SPR Heatmap (Fixed Gradient: Green to Red)", spr_mean)

# Plot FR heatmap with fixed gradient
plot_fixed_gradient_heatmap(fr_matrix, "FR Heatmap (Fixed Gradient: Green to Red)", fr_mean)