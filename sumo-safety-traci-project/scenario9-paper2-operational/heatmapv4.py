import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import Normalize, LinearSegmentedColormap

# Define the range for data to include in the heatmap
x_start = "E1_200m"      # Start distance (inclusive)
x_end = "E1_2200m"     # End distance (inclusive)
y_start = 2444.6             # Start time (inclusive)
y_end = 5744.6               # End time (inclusive)

# Toggles
annot_toggle = True
selective_labels_toggle = False

# Load the CSV file
file_path = "ratios_results.csv" 
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

# # Cap values to the upper bound of 1
# spr_matrix = spr_matrix.clip(upper=1.0)
# fr_matrix = fr_matrix.clip(upper=1.0)

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

# Replace values greater than 1 with ">1" for display while retaining numeric values for the heatmap
def apply_display_format(matrix):
    display_matrix = matrix.copy()
    for col in display_matrix.columns:
        display_matrix[col] = display_matrix[col].map(lambda x: ">1" if x > 1 else f"{x:.2f}")
    return display_matrix

spr_display_matrix = apply_display_format(spr_matrix)
fr_display_matrix = apply_display_format(fr_matrix)

# Adjust x-axis labels for reversed distances
def reverse_x_labels(matrix):
    numeric_columns = [int(col.split('_')[1][:-1]) for col in matrix.columns]
    max_value = max(numeric_columns)
    reversed_labels = [-1 * (max_value - col) for col in numeric_columns]
    return [f"{label}" for label in reversed_labels]  # Explicitly cast to string with negative sign


x_labels = reverse_x_labels(spr_matrix)

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

# Updated function to plot heatmap with SOI in the top-left corner
def plot_fixed_gradient_heatmap(matrix, display_matrix, title, x_labels, x_label_freq=1, soi_value=None, output_file=None):
    cmap, norm = get_fixed_gradient_colour_map()
    plt.figure(figsize=(10, 7))  # Adjust figure size for similar layout
    ax = sns.heatmap(
        matrix,
        cmap=cmap,
        norm=norm,  # Apply fixed gradient normalization
        annot=display_matrix if annot_toggle else None,
        fmt="",  # Disable default formatting for annotation
        cbar=True,
        cbar_kws={"label": "Operational Impact Rating"},
        annot_kws={"fontsize": 8, "rotation": 45},  # Added rotation for annotation labels
    )
    cbar = ax.collections[0].colorbar
    cbar.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])  # Show only the thresholds
    cbar.set_ticklabels(["0.00", "0.25", "0.50", "0.75", "1.00"])

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

    # Set custom x-axis labels with frequency control
    plt.xticks(
        ticks=np.arange(0.5, len(x_labels), x_label_freq),  # Display every x_label_freq-th label
        labels=x_labels[::x_label_freq],
        fontsize=10, rotation=90
    )

    # Add the SOI value to the top-left corner
    if soi_value is not None:
        plt.text(
            x=0.5, y=0.5,
            s=f"SOI: {soi_value:.3f}",
            fontsize=12, color="black", fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="black"),  # Add white box
        )

    plt.tight_layout()  # Adjust layout to prevent clipping
    # Save to PDF if an output file is specified
    if output_file:
        plt.savefig(output_file, format='pdf', dpi=300)

    plt.show()

# Call the plotting functions with the SOI value
plot_fixed_gradient_heatmap(spr_matrix, spr_display_matrix, "SPR Heatmap (Fixed Gradient: Green to Red)", x_labels, x_label_freq=5, soi_value=spr_mean, output_file="SPR_Heatmap.pdf")
plot_fixed_gradient_heatmap(fr_matrix, fr_display_matrix, "FR Heatmap (Fixed Gradient: Green to Red)", x_labels, x_label_freq=5, soi_value=fr_mean, output_file="FR_Heatmap.pdf")
