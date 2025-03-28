import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import Normalize, LinearSegmentedColormap

# Define the range for data to include in the heatmap
x_start = "E1_0m"      # Start distance (inclusive)
x_end = "E1_3000m"     # End distance (inclusive)
y_start = 2444.6             # Start time (inclusive)
y_end = 6644.6               # End time (inclusive)

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
def plot_side_by_side_with_shared_colorbar(spr_matrix, fr_matrix, spr_display_matrix, fr_display_matrix, 
                                           spr_mean, fr_mean, x_labels, x_label_freq=1, output_file="heatmaps.png"):
    cmap, norm = get_fixed_gradient_colour_map()

    # Create a figure with 2 subplots side by side
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={'width_ratios': [1, 1], 'wspace': 0.3})
    cbar_ax = fig.add_axes([0.93, 0.2, 0.02, 0.6])  # Colorbar position: [left, bottom, width, height]

    # Plot the SPR heatmap
    sns.heatmap(
        spr_matrix, cmap=cmap, norm=norm, annot=spr_display_matrix if annot_toggle else None,
        fmt="", cbar=False, ax=axes[0],
        annot_kws={"fontsize": 8, "rotation": 45}
    )
    axes[0].set_title("SPR Heatmap", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Distance (m)", fontsize=12)
    axes[0].set_ylabel("Time Intervals (s)", fontsize=12)

    # Set custom x-axis labels for SPR
    axes[0].set_xticks(np.arange(0, len(x_labels), x_label_freq))
    axes[0].set_xticklabels(x_labels[::x_label_freq], fontsize=10, rotation=90)

    # Add SOI value for SPR in the top-left corner
    axes[0].text(
        x=0.02, y=1.02,
        s=f"SOI: {spr_mean:.3f}",
        fontsize=12, color="black", fontweight="bold",
        bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.3"),
        transform=axes[0].transAxes, ha="left", va="center"
    )

    # Plot the FR heatmap
    sns.heatmap(
        fr_matrix, cmap=cmap, norm=norm, annot=fr_display_matrix if annot_toggle else None,
        fmt="", cbar=False, ax=axes[1],
        annot_kws={"fontsize": 8, "rotation": 45}
    )
    axes[1].set_title("FR Heatmap", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Distance (m)", fontsize=12)
    axes[1].set_ylabel("")

    # Set custom x-axis labels for FR
    axes[1].set_xticks(np.arange(0, len(x_labels), x_label_freq))
    axes[1].set_xticklabels(x_labels[::x_label_freq], fontsize=10, rotation=90)

    # Add SOI value for FR in the top-left corner
    axes[1].text(
        x=0.02, y=1.02,
        s=f"SOI: {fr_mean:.3f}",
        fontsize=12, color="black", fontweight="bold",
        bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.3"),
        transform=axes[1].transAxes, ha="left", va="center"
    )

    # Configure the shared colorbar
    cbar = fig.colorbar(
        plt.cm.ScalarMappable(cmap=cmap, norm=norm),
        cax=cbar_ax,
        orientation="vertical"
    )
    cbar.set_label("Operational Impact Rating", fontsize=12)
    cbar.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(["0.00", "0.25", "0.50", "0.75", "1.00"])

    plt.tight_layout(rect=[0, 0, 0.9, 1])  # Adjust layout to accommodate colorbar
    plt.savefig(output_file, dpi=300)  # Save the figure as a high-quality PNG
    plt.show()

plot_side_by_side_with_shared_colorbar(
    spr_matrix, fr_matrix, spr_display_matrix, fr_display_matrix,
    spr_mean, fr_mean, x_labels, x_label_freq=5, output_file="heatmaps_side_by_side.png"
)

