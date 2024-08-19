import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

""" ********************** plotting for resource_pool ************************** """
def resource_pool_plot_results(resource_pool, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'ResourcePool')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    summary_data = []

    """Calculate and print summary statistics for each category, and plot task times."""
    for category in resource_pool.ledger:
        tasks = resource_pool.ledger[category]
        completed_tasks = [t for t in tasks if t['completion_time'] is not None]
        waiting_times = [t['waiting_time'] for t in tasks if t['waiting_time'] is not None]
        completion_times = [t['completion_time'] for t in completed_tasks if t['completion_time']]

        total_tasks = len(tasks)
        total_completed_tasks = len(completed_tasks)
        total_average_completion_time = np.mean(completion_times) if completion_times else 0
        total_average_waiting_time = np.mean(waiting_times) if waiting_times else 0

        print(f"Category {category}: Total Tasks = {total_tasks}, Completed Tasks = {total_completed_tasks}")
        print(f"Average Completion Time = {total_average_completion_time}")
        print(f"Average Waiting Time = {total_average_waiting_time}")

        # Append summary data for this category
        summary_data.append({
            'Category': category,
            'Total Tasks': total_tasks,
            'Completed Tasks': total_completed_tasks,
            'Average Completion Time': total_average_completion_time,
            'Average Waiting Time': total_average_waiting_time
        })

        # Plot completion and waiting times
        plt.figure(figsize=(20, 5))
        plt.subplot(131)
        plt.plot(waiting_times, 'ro-', label='Waiting Time')
        plt.title(f'Waiting Times for Category {category}\n(includes unfinished tasks)', fontsize=20)
        plt.xlabel('Task Index', fontsize=18)
        plt.ylabel('Time (s)', fontsize=18)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        plt.subplot(132)
        plt.plot(completion_times, 'bo-', label='Completion Time')
        plt.title(f'Completion Times for Category {category}', fontsize=20)
        plt.xlabel('Task Index', fontsize=18)
        plt.ylabel('Time (s)', fontsize=18)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        turnaround_times = [sum(x) for x in zip(completion_times, waiting_times)]
        plt.subplot(133)
        plt.plot(turnaround_times, 'go-', label='Turnaround Time')
        plt.title(f'Turnaround Times for Category {category}', fontsize=20)
        plt.xlabel('Task Index', fontsize=18)
        plt.ylabel('Time (s)', fontsize=18)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        plt.tight_layout()
        plot_path = os.path.join(subdirectory_path, f'Completion_and_Waiting_Times_for_Category_{category}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Completion and Waiting Time Plot saved to {plot_path}")

        # Ensure all lists are of the same length
        max_length = max(len(waiting_times), len(completion_times), len(turnaround_times))
        waiting_times.extend([None] * (max_length - len(waiting_times)))
        completion_times.extend([None] * (max_length - len(completion_times)))
        turnaround_times.extend([None] * (max_length - len(turnaround_times)))

        # Save the data to CSV
        data = {
            'waiting_times': waiting_times,
            'completion_times': completion_times,
            'turnaround_times': turnaround_times
        }
        df = pd.DataFrame(data)
        csv_path = os.path.join(subdirectory_path, f'Completion_and_Waiting_Times_for_Category_{category}.csv')
        df.to_csv(csv_path, index=False)
        print(f"CSV saved to {csv_path}")

        # Extract data lists from the resource pool
        times = resource_pool.time_series[category]['times']
        waiting_times = resource_pool.time_series[category]['waiting_times']
        completion_times = resource_pool.time_series[category]['completion_times']

        # Filter out records where completion times are None
        filtered_data = [
            (t, w, c) for t, w, c in zip(times, waiting_times, completion_times)
            if c is not None
        ]

        # Create DataFrame from filtered data if not empty
        if filtered_data:
            df = pd.DataFrame(filtered_data, columns=['times', 'waiting_times', 'completion_times'])

            # Additional logic to process this DataFrame
            df['turnaround_time'] = df['waiting_times'] + df['completion_times']
            df['time_bin'] = pd.cut(df['times'], bins=np.arange(0, simulation_time + interval, interval), right=False)
            avg_data = df.groupby('time_bin', observed=True)[['waiting_times', 'completion_times', 'turnaround_time']].mean()

            # Plotting only the bins with data
            if not avg_data.empty:
                mid_points = [interval.left + (interval.right - interval.left) / 2 for interval in avg_data.index]
                plt.figure(figsize=(12, 6))
                plt.plot(mid_points, avg_data['waiting_times'], label='Avg. Waiting Time', marker='o')
                plt.plot(mid_points, avg_data['completion_times'], label='Avg. Completion Time', marker='x')
                plt.plot(mid_points, avg_data['turnaround_time'], label='Avg. Turnaround Time', marker='s')
                plt.title(f"Avg. Times for Category {category}", fontsize=20)
                plt.xlabel('Simulation Time', fontsize=18)
                plt.ylabel('Avg. Time (s)', fontsize=18)
                plt.legend()
                plt.grid(True)
                plt.xlim([0, simulation_time])
                plt.ylim(bottom=0)
                plt.xticks(fontsize=16)  
                plt.yticks(fontsize=16) 
                plot_path = os.path.join(subdirectory_path, f'Avg_Times_for_Category_{category}_Over_Simulation_Time.png')
                plt.savefig(plot_path)
                plt.close()
                print(f"Average Times for Category {category} Plot saved to {plot_path}")

                # Save the averaged data to CSV
                avg_data['mid_points'] = mid_points
                csv_path = os.path.join(subdirectory_path, f'Avg_Times_for_Category_{category}_Over_Simulation_Time.csv')
                avg_data.to_csv(csv_path, index=False)
                print(f"CSV saved to {csv_path}")
            else:
                print(f"No data available for plotting in category {category}.")

    # Save summary data to CSV
    summary_df = pd.DataFrame(summary_data)
    summary_csv_path = os.path.join(subdirectory_path, 'summary_statistics.csv')
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"Summary statistics saved to {summary_csv_path}")

""" ********************** plotting faults experienced by tasks from ResourcePool ************************** """
def plot_task_failures_and_completion_times(resource_pool, output_directory):
    """
    Plots task failures and completion times, ensuring failure counts are properly incremented,
    with different colors for each task category.
    
    Parameters:
    - resource_pool: ResourcePool object containing task interruption records.
    - output_directory: Directory where the plots will be saved.
    """
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(output_directory, 'Faults')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    task_interruption_record = resource_pool.task_interruption_record
    ledger = resource_pool.ledger

    # Extract data for plotting
    failure_times = task_interruption_record['fault_identification_time']
    task_ids = task_interruption_record['task_id']
    processor_ids = task_interruption_record['processor_id']

    # Calculate completion times for failed tasks and their categories
    completion_times = []
    categories = []
    for task_id in task_ids:
        task_completion_time = None
        task_category = None
        # Loop through the ledger to find the task's category and completion time
        for category, records in ledger.items():
            for record in records:
                if record['task_id'] == task_id:
                    task_category = category
                    task_completion_time = record.get('completion_time', None)  # Fetch completion time
                    break
            if task_category is not None:
                break
        completion_times.append(task_completion_time)
        categories.append(task_category)

    # Create a DataFrame with all the necessary data
    data = {
        'failure_times': failure_times,
        'task_ids': task_ids,
        'processor_ids': processor_ids,
        'completion_times': completion_times,
        'categories': categories
    }
    df = pd.DataFrame(data)

    # Initialize a dictionary to keep track of failure counts for each task ID
    task_failure_counts = {}

    # Update failure counts sequentially for each task ID as they fail
    failure_counts = []
    for idx, row in df.iterrows():
        task_id = row['task_ids']
        if task_id not in task_failure_counts:
            task_failure_counts[task_id] = 1
        else:
            task_failure_counts[task_id] += 1
        failure_counts.append(task_failure_counts[task_id])

    # Assign the computed failure counts back to the DataFrame
    df['failure_counts'] = failure_counts

    # Create a colormap for the categories
    unique_categories = df['categories'].unique()
    colors = plt.cm.get_cmap('tab10', len(unique_categories))
    category_color_map = {category: colors(i) for i, category in enumerate(unique_categories)}

    # Create figure and axes for the plot
    fig, ax = plt.subplots()

    # Group task IDs by their failure times and stack them vertically using '\n'.join()
    task_ids_by_time = df.groupby(['failure_times', 'failure_counts'])['task_ids'].apply(lambda x: '\n'.join(x.astype(str)))

    # Track which categories have been plotted for the legend
    plotted_categories = set()

    # Plot the failure counts, label the task IDs at the correct failure count position with colors for each category
    for idx, row in df.iterrows():
        color = category_color_map[row['categories']]
        label = f'Category {row["categories"]}' if row['categories'] not in plotted_categories else ""
        ax.scatter(row['failure_times'], row['failure_counts'], color=color, s=100, label=label)

        # Add the category to the plotted categories set
        plotted_categories.add(row['categories'])

        # Stack task IDs vertically using '\n'.join()
        task_ids_label = task_ids_by_time[(row['failure_times'], row['failure_counts'])]
        ax.text(row['failure_times'], row['failure_counts'] + 0.1, task_ids_label, 
                ha='center', fontsize=14)

    # Set axis labels and limits
    ax.set_xlabel('Simulation Time (s)', fontsize=18)
    ax.set_ylabel('Failure Counts', fontsize=18)
    ax.set_xlim(0, 200)

    # Get the maximum failure count, ensuring it is not NaN or Inf
    max_failure_count = df['failure_counts'].max()

    # Handle the case where max_failure_count is NaN or None by defaulting to 0
    if pd.isna(max_failure_count) or np.isinf(max_failure_count):
        max_failure_count = 0

    # Set the y-axis limits, ensuring enough space
    ax.set_ylim(0, max_failure_count + 1)

    # plt.title('Number of Failures Over Time', fontsize=20)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 

    # Add legend for categories
    ax.legend(loc="upper left", fontsize=16)


    fig.tight_layout()

    # Save the plot
    scatter_plot_file = os.path.join(subdirectory_path, 'task_failures_scatter_plot_colored.png')
    plt.savefig(scatter_plot_file)
    plt.close()
    print(f"Scatter plot saved to {scatter_plot_file}")

    # Save the complete DataFrame (including completion times) to CSV
    csv_path = os.path.join(subdirectory_path, 'task_failures_and_completion_times.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")





""" ********************** plotting for processor ************************** """
def processor_visualize_task_data(processors, directory):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    for processor in processors:
        task_times = [task.total_processing_time for task in processor.task_records]
        data_arrival_times = [task.data_arrival_time for task in processor.task_records]

        plt.figure(figsize=(14, 7))
        
        # Plot for processing times
        plt.subplot(1, 2, 1)
        plt.bar(range(len(task_times)), task_times, color='b')
        plt.title(f'Processing Times\nfor Tasks on Processor {processor.processor_id}', fontsize=20)
        plt.xlabel('Task Index', fontsize=18)
        plt.ylabel('Processing Time', fontsize=18)
        plt.xticks(range(len(task_times)), fontsize=16)  # Set X-axis from 0 to the number of tasks
        plt.yticks(fontsize=16)

        # Plot for data arrival times
        plt.subplot(1, 2, 2)
        plt.bar(range(len(data_arrival_times)), data_arrival_times, color='r')
        plt.title(f'Data Arrival Times\nfor Tasks on Processor {processor.processor_id}', fontsize=20)
        plt.xlabel('Task Index', fontsize=18)
        plt.ylabel('Data Arrival Time', fontsize=18)
        plt.xticks(range(len(data_arrival_times)), fontsize=16)  # Set X-axis from 0 to the number of tasks
        plt.yticks(fontsize=16)

        plt.tight_layout()
        plot_path = os.path.join(subdirectory_path, f'Data_Arrival_Times_for_Tasks_on_Processor_{processor.processor_id}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Data Arrival Times for Tasks on Processor {processor.processor_id} Plot saved to {plot_path}")

        # Save the data to CSV
        data = {
            'task_times': task_times,
            'data_arrival_times': data_arrival_times
        }
        df = pd.DataFrame(data)
        csv_path = os.path.join(subdirectory_path, f'Data_Arrival_Times_for_Tasks_on_Processor_{processor.processor_id}.csv')
        df.to_csv(csv_path, index=False)
        print(f"CSV saved to {csv_path}")


def processor_visualize_processor_performance(processors, directory):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    all_processing_times = [task.total_processing_time for processor in processors for task in processor.task_records]
    all_data_arrival_times = [task.data_arrival_time for processor in processors for task in processor.task_records]

    plt.figure(figsize=(14, 7))
    plt.subplot(1, 2, 1)
    plt.hist(all_processing_times, bins=20, color='blue', alpha=0.7)
    plt.title('Histogram: Distribution of Processing\nTimes Across All Processors', fontsize=20)
    plt.xlabel('Processing Time', fontsize=18)
    plt.ylabel('Frequency', fontsize=18)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 

    plt.subplot(1, 2, 2)
    plt.hist(all_data_arrival_times, bins=20, color='red', alpha=0.7)
    plt.title('Histogram: Distribution of Data\nArrival Times Across All Processors', fontsize=20)
    plt.xlabel('Data Arrival Time', fontsize=18)
    plt.ylabel('Frequency', fontsize=18)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 

    plt.tight_layout()
    plot_path = os.path.join(subdirectory_path, 'Histogra_Distribution_of_Data_Arrival_Times_Across_All_Processors.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Histogram_Distribution of Data Arrival Times Across All Processors Plot saved to {plot_path}")

    # Save the data to CSV
    data = {
        'all_processing_times': all_processing_times,
        'all_data_arrival_times': all_data_arrival_times
    }
    df = pd.DataFrame(data)
    csv_path = os.path.join(subdirectory_path, 'Distribution_of_Data_Arrival_Times_Across_All_Processors.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")

def processor_plot_average_data_arrival_times(processors, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Initialize a plot
    plt.figure(figsize=(10, 5))

    # Iterate through each processor to collect and plot their data arrival times
    for processor in processors:
        data_points = []
        for task in processor.task_records:
            if hasattr(task, 'data_arrival_time') and task.data_arrival_time is not None:
                # Collect task request time and arrival time
                data_points.append((task.data_received_time, task.data_arrival_time))
        
        if data_points:
            # Create a DataFrame from the collected data points for the current processor
            df = pd.DataFrame(data_points, columns=['data_received_time', 'data_arrival_time'])
            
            # Create time bins from the earliest to the latest time in the dataset, stepped by interval
            time_bins = np.arange(0, simulation_time + interval, interval)
            
            # Group by these time bins and calculate the mean data arrival time for each
            df['time_bin'] = pd.cut(df['data_received_time'], bins=time_bins, right=False)
            grouped = df.groupby('time_bin', observed=True)['data_arrival_time'].mean().reset_index()
            
            # Prepare the time bins for plotting (using the middle point of each bin)
            grouped['time_bin_mid'] = grouped['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
            
            # Plotting
            plt.plot(grouped['time_bin_mid'], grouped['data_arrival_time'], marker='o', linestyle='-', label=f'Processor {processor.processor_id}')
        else:
            print(f"No data arrival times available for Processor {processor.processor_id}.")

    plt.title(f'Avg. Data Arrival Time per {interval}s', fontsize=20)
    plt.xlabel('Simulation Time (s)', fontsize=18)
    plt.ylabel('Avg. Data Arrival Time (s)', fontsize=18)
    plt.xlim([0, simulation_time])
    plt.ylim(bottom=0)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 
    plt.legend()
    plt.grid(True)

    plot_path = os.path.join(subdirectory_path, 'average_data_arrival_times.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"average_data_arrival_times Plot saved to {plot_path}")

    # Save the data to CSV
    if data_points:
        data = {
            'time_bin_mid': grouped['time_bin_mid'],
            'avg_data_arrival_time': grouped['data_arrival_time']
        }
        df = pd.DataFrame(data)
        csv_path = os.path.join(subdirectory_path, 'average_data_arrival_times.csv')
        df.to_csv(csv_path, index=False)
        print(f"CSV saved to {csv_path}")

def processor_plot_average_data_arrival_times(processors, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'processors')
    
    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Group processors by category
    category_groups = {}
    for processor in processors:
        category = processor.category
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(processor)

    # Iterate through each category
    for category, group_processors in category_groups.items():
        # Initialize a plot
        plt.figure(figsize=(10, 5))

        # Process each processor in this category
        for processor in group_processors:
            data_points = []
            for task in processor.task_records:
                if hasattr(task, 'data_arrival_time') and task.data_arrival_time is not None:
                    # Collect task request time and arrival time
                    data_points.append((task.data_received_time, task.data_arrival_time))
            
            if data_points:
                # Create a DataFrame from the collected data points for the current processor
                df = pd.DataFrame(data_points, columns=['data_received_time', 'data_arrival_time'])
                
                # Create time bins from the earliest to the latest time in the dataset, stepped by interval
                time_bins = np.arange(0, simulation_time + interval, interval)
                
                # Group by these time bins and calculate the mean data arrival time for each
                df['time_bin'] = pd.cut(df['data_received_time'], bins=time_bins, right=False)
                grouped = df.groupby('time_bin', observed=True)['data_arrival_time'].mean().reset_index()
                
                # Prepare the time bins for plotting (using the middle point of each bin)
                grouped['time_bin_mid'] = grouped['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                
                # Plotting
                plt.plot(grouped['time_bin_mid'], grouped['data_arrival_time'], marker='o', linestyle='-', label=f'Processor {processor.processor_id}')
            else:
                print(f"No data arrival times available for Processor {processor.processor_id}.")

        plt.title(f'Category {category}: Avg. Data Arrival Time per {interval}s', fontsize=20)
        plt.xlabel('Simulation Time (s)', fontsize=18)
        plt.ylabel('Avg. Data Arrival Time (s)', fontsize=18)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.legend()
        plt.grid(True)

        plot_path = os.path.join(subdirectory_path, f'average_data_arrival_times_category_{category}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Average Data Arrival Times plot for Category {category} saved to {plot_path}")

        # Save the data to CSV
        if data_points:
            data = {
                'time_bin_mid': grouped['time_bin_mid'],
                'avg_data_arrival_time': grouped['data_arrival_time']
            }
            df = pd.DataFrame(data)
            csv_path = os.path.join(subdirectory_path, f'average_data_arrival_times_category_{category}.csv')
            df.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

def processor_visualize_average_performance(processors, directory):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    avg_processing_times = []
    avg_data_arrival_times = []
    processor_ids = []

    for processor in processors:
        if processor.task_records:
            avg_proc_time = sum([task.total_processing_time for task in processor.task_records]) / len(processor.task_records)
            avg_data_time = sum([task.data_arrival_time for task in processor.task_records]) / len(processor.task_records)
            avg_processing_times.append(avg_proc_time)
            avg_data_arrival_times.append(avg_data_time)
            processor_ids.append(processor.processor_id)

    ind = np.arange(len(processor_ids))  # the x locations for the groups
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.bar(ind - width/2, avg_processing_times, width, label='Avg Processing Time')
    rects2 = ax.bar(ind + width/2, avg_data_arrival_times, width, label='Avg Data Arrival Time')

    ax.set_xlabel('Processor ID', fontsize=18)
    ax.set_ylabel('Time (s)', fontsize=18)
    ax.set_title('Avg. Processing and\nData Arrival Times by Processor', fontsize=20)
    ax.set_xticks(ind)
    ax.set_xticklabels(processor_ids)
    ax.legend()

    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)

    fig.tight_layout()
    plot_path = os.path.join(subdirectory_path, 'Average_Processing_and_Data_Arrival_Times_by_Processor.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Average Processing and Data Arrival Times by Processor plot saved to {plot_path}")

    # Save the data to CSV
    data = {
        'processor_ids': processor_ids,
        'avg_processing_times': avg_processing_times,
        'avg_data_arrival_times': avg_data_arrival_times
    }
    df = pd.DataFrame(data)
    csv_path = os.path.join(subdirectory_path, 'Average_Processing_and_Data_Arrival_Times_by_Processor.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")

""" ********************** plotting for DTN ************************** """
def dtn_plot_data_handling_times(dtn, directory):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'dtn')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Extract data preparation times and prepare for plotting
    task_ids = []
    handling_times = []
    for task_id, times in dtn.data_preparation_times.items():
        if times['start_preparation_time'] and times['end_preparation_time']:
            duration = times['end_preparation_time'] - times['start_preparation_time']
            task_ids.append(task_id)
            handling_times.append(duration)

    if not handling_times:
        print("No data handling times to display.")
        return

    # Plotting the handling times
    plt.figure(figsize=(10, 5))
    plt.bar(task_ids, handling_times, color='blue')
    plt.title('DTN Data Handling Times', fontsize=20)
    plt.xlabel('Task ID', fontsize=18)
    plt.ylabel('Data Handling Time (s)', fontsize=18)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 
    plt.grid(True)

    plot_path = os.path.join(subdirectory_path, 'DTN_Data_Handling_Times.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"DTN Data Handling Times by DTN plot saved to {plot_path}")

    # Save the data to CSV
    data = {
        'task_ids': task_ids,
        'handling_times': handling_times
    }
    df = pd.DataFrame(data)
    csv_path = os.path.join(subdirectory_path, 'DTN_Data_Handling_Times.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")

def dtn_plot_data_handling_time_series(dtn, directory, simulation_time, interval):
    """Plots the average DTN data preparation times over simulation time intervals."""
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'dtn')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Extract preparation times and their corresponding start times
    times = []
    preparation_durations = []
    for task_id, timings in dtn.data_preparation_times.items():
        if timings['start_preparation_time'] and timings['end_preparation_time']:
            start = timings['start_preparation_time']
            end = timings['end_preparation_time']
            duration = end - start
            times.append(start)
            preparation_durations.append(duration)

    # Prepare DataFrame
    df = pd.DataFrame({
        'time': times,
        'duration': preparation_durations
    })

    # Define time bins and group data
    bins = np.arange(0, simulation_time + interval, interval)
    df['time_bin'] = pd.cut(df['time'], bins=bins, right=False)
    avg_durations = df.groupby('time_bin', observed=True)['duration'].mean().reset_index()

    # Prepare the time bins for plotting (using the middle point of each bin)
    avg_durations['time_bin_mid'] = avg_durations['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)

    # Plotting
    plt.figure(figsize=(10, 5))
    plt.plot(avg_durations['time_bin_mid'], avg_durations['duration'], marker='o', linestyle='-', color='blue')
    plt.title(f'Avg. DTN Data Handling Time per {interval}s', fontsize=20)
    plt.xlabel('Simulation Time (s)', fontsize=18)
    plt.ylabel('Avg. Data Handling Time (s)', fontsize=18)
    plt.xlim([0, simulation_time])
    plt.ylim(bottom=0)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 
    plt.grid(True)
    plot_path = os.path.join(subdirectory_path, f'Average_DTN_Data_Handling_Time_per_{interval}s.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Average DTN Data Handling Time per {interval}s by DTN plot saved to {plot_path}")

    # Save the data to CSV
    avg_durations.to_csv(os.path.join(subdirectory_path, f'Average_DTN_Data_Handling_Time_per_{interval}s.csv'), index=False)
    print(f"CSV saved to {subdirectory_path}")

"""*********************** visualization function - for routers ****************************"""
def router_plot_router_load(routers, aqm, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'routers')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)


    if aqm == 'fifo':
        plt.figure(figsize=(10, 5))
        all_data = pd.DataFrame()  # Initialize an empty DataFrame to store all routers' data
        for router in routers:
            if router.load_history:
                times, loads = zip(*router.load_history)
                plt.plot(times, loads, label=f'Router {router.router_id}')

                # Collecting data for CSV
                router_df = pd.DataFrame({
                    'time': times,
                    f'Router_{router.router_id}_load': loads
                })

                if all_data.empty:
                    all_data = router_df
                else:
                    all_data = pd.merge(all_data, router_df, on='time', how='outer')

        # Save the data to CSV
        if not all_data.empty:
            csv_path = os.path.join(subdirectory_path, 'Total_Queue_Load_Over_Time.csv')
            all_data.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

        plt.title('Total Queue Load Over Time', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)
        plot_path = os.path.join(subdirectory_path, 'Total_Queue_Load_Over_Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Queue Load Over Time plot saved at {plot_path}")


        # Plot average load over time for all routers
        plt.figure(figsize=(10, 5))
        all_avg_data = pd.DataFrame()  # Initialize an empty DataFrame to store averaged data from all routers
        for router in routers:
            if router.load_history:
                df = pd.DataFrame(router.load_history, columns=['time', 'load'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['load'].mean().reset_index()
                time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                plt.plot(time_bins_mid, df_avg['load'], label=f'Router {router.router_id}')

                # Plotting the data
                plt.plot(time_bins_mid, df_avg['load'], label=f'Router {router.router_id}')

                # Collecting data for CSV
                avg_df = pd.DataFrame({
                    'time_bin_mid': time_bins_mid,
                    f'Router_{router.router_id}_avg_load': df_avg['load'].values
                })

                if all_avg_data.empty:
                    all_avg_data = avg_df
                else:
                    all_avg_data = pd.merge(all_avg_data, avg_df, on='time_bin_mid', how='outer')

        # Save the averaged data to CSV
        if not all_avg_data.empty:
            csv_path = os.path.join(subdirectory_path, 'Average_Load_Over_Time.csv')
            all_avg_data.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")


        plt.title('Avg. Load Over Time', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Avg. Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)
        plot_path = os.path.join(subdirectory_path, 'Average_Load_Over_Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Average Load Over Time plot saved at {plot_path}")


    elif aqm == 'fq':
        # Plot total load over time for each router
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.load_history:
                times = []
                total_loads = []
                for time in sorted(set([t for t, _, _ in router.load_history])):
                    total_load_at_time = sum(load for t, q_id, load in router.load_history if t == time)
                    times.append(time)
                    total_loads.append(total_load_at_time)
                plt.plot(times, total_loads, label=f'Router {router.router_id}')

        plt.title('Total Queue Load Over Time', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        plot_path = os.path.join(subdirectory_path, 'Total_Router_Load_Over_Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Total Queue Load Over Time plot saved at {plot_path}")

        # Save the data to CSV
        if times:
            data = {
                'times': times,
                'total_loads': total_loads
            }
            df = pd.DataFrame(data)
            csv_path = os.path.join(subdirectory_path, 'Total_Router_Load_Over_Time.csv')
            df.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

        # Plot load for each queue within each router
        for router in routers:
            plt.figure(figsize=(10, 5))
            all_queue_data = pd.DataFrame()  # Initialize an empty DataFrame to store all queues' data
            for queue_id, queue in router.queues.items():
                if router.load_history:
                    times, loads = zip(*[(time, load) for time, q_id, load in router.load_history if q_id == queue_id])
                    plt.plot(times, loads, label=f'Queue {queue_id}')
                  
                  
                    # Storing data for CSV
                    queue_df = pd.DataFrame({
                        'time': times,
                        f'Queue_{queue_id}_load': loads
                    })
                    
                    if all_queue_data.empty:
                        all_queue_data = queue_df
                    else:
                        all_queue_data = pd.merge(all_queue_data, queue_df, on='time', how='outer')

            # Save the data to CSV
            if not all_queue_data.empty:
                csv_path = os.path.join(subdirectory_path, f'Router_{router.router_id}_Load_Over_Time.csv')
                all_queue_data.to_csv(csv_path, index=False)
                print(f"CSV saved to {csv_path}")


            # plt.title(f'Load Over Time for Router {router.router_id}', fontsize=20)
            plt.xlabel('Time', fontsize=18)
            plt.ylabel('Number of Queued Packets', fontsize=18)
            # plt.legend(fontsize=16)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)  
            plt.yticks(fontsize=16) 
            plt.grid(True)

            plot_path = os.path.join(subdirectory_path, f'Router_{router.router_id}_Load_Over_Time.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"Saved individual queue load plot for Router {router.router_id} to {plot_path}")

        # Plot average load for each queue within each router
        for router in routers:
            plt.figure(figsize=(10, 5))
            all_avg_data = pd.DataFrame()  # To store average data for CSV

            for queue_id in router.queues.keys():
                queue_loads = [(time, load) for time, q_id, load in router.load_history if q_id == queue_id]
                if queue_loads:
                    df = pd.DataFrame(queue_loads, columns=['time', 'load'])
                    df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                    df_avg = df.groupby('time_bin', observed=True)['load'].mean().reset_index()
                    time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                    plt.plot(time_bins_mid, df_avg['load'], label=f'Queue {queue_id}')

                    # Create a DataFrame with time_bin_mid and avg_load, and merge it into all_avg_data
                    avg_df = pd.DataFrame({
                        'time_bin_mid': time_bins_mid,
                        f'Queue_{queue_id}_avg_load': df_avg['load'].values
                    })
                    
                    if all_avg_data.empty:
                        all_avg_data = avg_df
                    else:
                        all_avg_data = pd.merge(all_avg_data, avg_df, on='time_bin_mid', how='outer')

            # If data was collected, save it to CSV
            if not all_avg_data.empty:
                # Final check before saving
                # print(f"Final DataFrame for Router {router.router_id} before saving to CSV:")
                # print(all_avg_data.head())
                
                # Saving the DataFrame to CSV
                csv_path = os.path.join(subdirectory_path, f'Average_Queue_Load_Over_Time_Router_{router.router_id}.csv')
                all_avg_data.to_csv(csv_path, index=False)
                
                print(f"CSV saved to {csv_path}")

            plt.title(f'Avg. Load Over Time for Router {router.router_id}', fontsize=20)
            plt.xlabel('Time', fontsize=18)
            plt.ylabel('Avg. Number of Queued Packets', fontsize=18)
            plt.legend(fontsize=16)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)  
            plt.yticks(fontsize=16) 
            plt.grid(True)

            plot_path = os.path.join(subdirectory_path, f'Average_Queue_Load_Over_Time_Router_{router.router_id}.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"Average Queue Load Over Time plot for Router {router.router_id} saved at {plot_path}")

        # Plot total load over time for each router
        plt.figure(figsize=(10, 5))
        all_router_data = pd.DataFrame()  # Initialize an empty DataFrame to store all routers' data
        for router in routers:
            if router.load_history:
                times = []
                total_loads = []
                for time in sorted(set([t for t, _, _ in router.load_history])):
                    total_load_at_time = sum(load for t, q_id, load in router.load_history if t == time)
                    times.append(time)
                    total_loads.append(total_load_at_time)
                plt.plot(times, total_loads, label=f'Router {router.router_id}')

                # Storing data for CSV
                router_df = pd.DataFrame({
                    'time': times,
                    f'Router_{router.router_id}_total_load': total_loads
                })

                if all_router_data.empty:
                    all_router_data = router_df
                else:
                    all_router_data = pd.merge(all_router_data, router_df, on='time', how='outer')

        # Save the data to CSV
        if not all_router_data.empty:
            csv_path = os.path.join(subdirectory_path, 'Total_Router_Load_Over_Time.csv')
            all_router_data.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

        plt.title('Total Queue Load Over Time', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        plot_path = os.path.join(subdirectory_path, 'Total_Router_Load_Over_Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Total Queue Load Over Time plot saved at {plot_path}")

    else:
        raise ValueError(f'AQM Error: Unsupported AQM input "{aqm}"')

def router_calculate_and_plot_average_wait_times(routers, aqm, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'routers')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    if aqm == 'fifo':
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.packet_wait_times:
                df = pd.DataFrame(router.packet_wait_times, columns=['time', 'wait_time'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['wait_time'].mean().reset_index()

                time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                plt.plot(time_bins_mid, df_avg['wait_time'], label=f'Router {router.router_id}')

        plt.title('Avg. Packet Wait Times Over Time', fontsize=20)
        plt.xlabel('Time (s)', fontsize=18)
        plt.ylabel('Avg. Wait Time (s)', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16)
        plt.grid(True)

        plot_path = os.path.join(subdirectory_path, 'average_wait_times.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"average_wait_times {plot_path}")

        # Save the data to CSV
        if not df_avg.empty:
            avg_data = {
                'time_bin_mid': time_bins_mid,
                'avg_wait_time': df_avg['wait_time']
            }
            avg_df = pd.DataFrame(avg_data)
            csv_path = os.path.join(subdirectory_path, 'average_wait_times.csv')
            avg_df.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

    elif aqm == 'fq':
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.packet_wait_times:
                df = pd.DataFrame(router.packet_wait_times, columns=['time', 'wait_time'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['wait_time'].mean().reset_index()

                time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                plt.plot(time_bins_mid, df_avg['wait_time'], label=f'Router {router.router_id}')

        plt.title('Avg. Packet Wait Times Over Time', fontsize=20)
        plt.xlabel('Time (s)', fontsize=18)
        plt.ylabel('Avg. Wait Time (s)', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.grid(True)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 

        plot_path = os.path.join(subdirectory_path, 'average_wait_times.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"average_wait_times {plot_path}")

        # Save the data to CSV
        if not df_avg.empty:
            avg_data = {
                'time_bin_mid': time_bins_mid,
                'avg_wait_time': df_avg['wait_time']
            }
            avg_df = pd.DataFrame(avg_data)
            csv_path = os.path.join(subdirectory_path, 'average_wait_times.csv')
            avg_df.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")
        
    else:
        raise ValueError('AQM Error: Unsupported AQM input "{}"'.format(aqm))


def plot_tcp_metrics(tcp_connections, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'TCP_Metrics')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Define the metrics to plot
    metrics = ['cwnd', 'rtt', 'throughput', 'goodput', 'retransmissions']

    for metric in metrics:
        plt.figure(figsize=(10, 5))

        # Plot individual connection metrics
        for connection in tcp_connections:
            if metric == 'cwnd':
                df = connection.cwnd_log
                y_label = 'Congestion Window (segments)'
            elif metric == 'rtt':
                df = connection.rtt_log
                y_label = 'Round Trip Time (rtt) in s'
            elif metric == 'throughput':
                df = connection.throughput_log
                y_label = 'Throughput (MBps)'
            elif metric == 'goodput':
                df = connection.goodput_log
                y_label = 'Goodput (MBps)'
            elif metric == 'retransmissions':
                df = connection.retransmission_log
                y_label = 'Retransmissions (segments)'

            if not df.empty:
                plt.plot(df['time'], df[metric], label=f'Connection {connection.connection_id}')
        
        plt.title(f'{metric.capitalize()} Over Time for Each TCP Connection', fontsize=20)
        plt.xlabel('Time (s)', fontsize=18)
        plt.ylabel(y_label, fontsize=18)
        plt.grid(True)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16)
        plot_path = os.path.join(subdirectory_path, f'{metric}_individual_connections.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"{metric.capitalize()} Over Time for Each TCP Connection plot saved to {plot_path}")

        # Save the data to CSV
        if not df.empty:
            csv_path = os.path.join(subdirectory_path, f'{metric}_individual_connections.csv')
            df.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

        # Plot aggregate metrics
        aggregate_df = pd.DataFrame()
        for connection in tcp_connections:
            if metric == 'cwnd':
                df = connection.cwnd_log
            elif metric == 'rtt':
                df = connection.rtt_log
            elif metric == 'throughput':
                df = connection.throughput_log
            elif metric == 'goodput':
                df = connection.goodput_log
            elif metric == 'retransmissions':
                df = connection.retransmission_log
            
            if not df.empty:
                aggregate_df = pd.concat([aggregate_df, df[['time', metric]]])

        if not aggregate_df.empty:
            aggregate_df['time_bin'] = pd.cut(aggregate_df['time'], bins=np.arange(0, simulation_time + interval, interval), right=False)
            avg_data = aggregate_df.groupby('time_bin', observed=True)[metric].mean().reset_index()
            avg_data['time_bin_mid'] = avg_data['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)

            plt.figure(figsize=(14, 7))
            if metric == 'retransmissions':
                plt.bar(avg_data['time_bin_mid'], avg_data[metric], color='blue')
            else:
                plt.plot(avg_data['time_bin_mid'], avg_data[metric], marker='o', linestyle='-', color='blue')
            plt.title(f'Avg. {metric.capitalize()} Over Time Across All Connections', fontsize=20)
            plt.xlabel('Time (s)', fontsize=18)
            plt.ylabel(y_label, fontsize=18)
            plt.grid(True)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)  
            plt.yticks(fontsize=16)
            plot_path = os.path.join(subdirectory_path, f'average_{metric}_over_time.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"Avg. {metric.capitalize()} Over Time Across All Connections plot saved to {plot_path}")

            # Save the averaged data to CSV
            if not avg_data.empty:
                avg_csv_path = os.path.join(subdirectory_path, f'average_{metric}_over_time.csv')
                avg_data.to_csv(avg_csv_path, index=False)
                print(f"CSV saved to {avg_csv_path}")