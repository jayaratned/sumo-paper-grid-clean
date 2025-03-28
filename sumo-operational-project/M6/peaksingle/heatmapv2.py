import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Define the range for data to include in the heatmap
x_start = "204901083_0m"      # Start distance (inclusive)
x_end = "204901083_3000m"     # End distance (inclusive)
y_start = 51436.9       # Start time (inclusive)
y_end = 66136.9         # End time (inclusive)

# toggles
annot_toggle = False # True to display annotations, False to hide them
selective_labels_toggle = True # True to show every nth label, False to show all labels

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

# Calculate the interval dynamically based on adjusted_time
time_steps = np.diff(spr_matrix.index)  # Differences between consecutive times
interval_size = time_steps[0] if len(time_steps) > 0 else 0  # Use the first interval size


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


# Plot heatmap for a given matrix
def plot_heatmap(matrix, display_matrix, title, data_mean, selective_labels_toggle, show_every_nth_label=5):
    cmap, norm = get_colour_map()
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        matrix,
        cmap=cmap,
        norm=norm,
        annot=display_matrix if annot_toggle else None,
        fmt="" if annot_toggle else None,
        cbar=True,
        cbar_kws={"label": "Operational Impact Rating"},
        annot_kws={"rotation": 90} if annot_toggle else None,
    )
    plt.title(title)
    plt.xlabel("Distance (m)")
    plt.ylabel("Time Intervals (s)")

    # Generate y-axis interval labels with selective toggle
    y_ticks, interval_labels = generate_interval_labels(
        matrix, show_every_nth_label, selective_labels_toggle
    )

        # Set the y-axis labels
    plt.yticks(
        ticks=y_ticks + 0.5,  # Adjust ticks to align with heatmap rows
        labels=interval_labels,
        rotation=0,
    )

    # Add the mean value to the top-left corner of the plot
    plt.text(
        x=-0.5, y=-0.5,
        s=f"SOI: {data_mean:.3f}",
        fontsize=12, color="black", fontweight="bold",
    )

    plt.xticks(rotation=90)
    plt.show()

# Plot SPR heatmap
plot_heatmap(
    spr_matrix,
    spr_display_matrix,
    "SPR Heatmap",
    spr_mean,
    selective_labels_toggle,  # Pass toggle for selective labels
    show_every_nth_label=10,  # Show every 10th label if toggle is enabled
)

# Plot FR heatmap
plot_heatmap(
    fr_matrix, 
    fr_display_matrix, 
    "SPR Heatmap", 
    fr_mean, 
    selective_labels_toggle,  # Pass toggle for selective labels
    show_every_nth_label=10,  # Show every 10th label if toggle is enabled
    )