import pandas as pd

def calculate_means(csv_file, start_time, end_time):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_file)

    # Filter the DataFrame for the specified time range
    time_filtered_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)]

    # Group by 'detector' and calculate the mean for each group
    means = time_filtered_df.groupby('detector').mean()

    return means

# Usage
csv_file = 'data/fivebyfive-1/outputs/upstream-test4/base_detector_data.csv'
start_time = 3600  # Start time for filtering
end_time = 5400    # End time for filtering
mean_values = calculate_means(csv_file, start_time, end_time)

print(mean_values)

# save means to csv
mean_values.to_csv('data/fivebyfive-1/outputs/upstream-test4/means-base.csv')
