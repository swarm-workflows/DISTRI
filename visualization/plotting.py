import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from entities.dtn import DTN


""" ********************** plotting for resource_pool ************************** """


def resource_pool_plot_results(resource_pool, directory, simulation_time, interval, site_id, plot_global_results=True):
    """
    Plots the resource pool results for a given site and optionally for global results.

    :param resource_pool: The ResourcePool instance for the site.
    :param directory: Base directory to save the plots and CSVs.
    :param simulation_time: The total simulation time.
    :param interval: Time interval for binning the data.
    :param site_id: ID of the site.
    :param plot_global_results: If True, plots global results from the common_ledger.
    """
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'ResourcePool')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    summary_data = []

    """Plotting site-specific results from the local ledger."""
    for category in resource_pool.site_ledger:
        jobs = resource_pool.site_ledger[category]  # Use site-specific ledger
        completed_jobs = [t for t in jobs if t['completion_time'] is not None]
        waiting_times = [t['waiting_time'] for t in jobs if t['waiting_time'] is not None]
        completion_times = [t['completion_time'] for t in completed_jobs]

        total_jobs = len(jobs)
        total_completed_jobs = len(completed_jobs)
        total_average_completion_time = np.mean(completion_times) if completion_times else 0
        total_average_waiting_time = np.mean(waiting_times) if waiting_times else 0

        print(f"Site {site_id} - Category {category}: Total Jobs = {total_jobs}, Completed Jobs = {total_completed_jobs}")
        print(f"Average Completion Time = {total_average_completion_time}")
        print(f"Average Waiting Time = {total_average_waiting_time}")

        # Append summary data for this category
        summary_data.append({
            'Site': site_id,
            'Category': category,
            'Total Jobs': total_jobs,
            'Completed Jobs': total_completed_jobs,
            'Average Completion Time': total_average_completion_time,
            'Average Waiting Time': total_average_waiting_time
        })

        # Extract and process time series data
        _process_and_plot_timeseries(resource_pool, category, simulation_time, interval, subdirectory_path, site_id)

        # Plot completion and waiting times for site-specific data
        _plot_times(waiting_times, completion_times, category, subdirectory_path, simulation_time, interval)

    # Save site-specific summary data to CSV
    summary_df = pd.DataFrame(summary_data)
    summary_csv_path = os.path.join(subdirectory_path, 'summary_statistics.csv')
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"Summary statistics saved to {summary_csv_path}")

    """Plotting global results if requested."""
    if plot_global_results:
        global_directory = os.path.join(directory, 'Global_ResourcePool')

        if not os.path.exists(global_directory):
            os.makedirs(global_directory)

        global_summary_data = []
        for category in resource_pool.common_ledger:
            jobs = resource_pool.common_ledger[category]
            completed_jobs = [t for t in jobs if t['completion_time'] is not None]
            waiting_times = [t['waiting_time'] for t in jobs if t['waiting_time'] is not None]
            completion_times = [t['completion_time'] for t in completed_jobs]

            total_jobs = len(jobs)
            total_completed_jobs = len(completed_jobs)
            total_average_completion_time = np.mean(completion_times) if completion_times else 0
            total_average_waiting_time = np.mean(waiting_times) if waiting_times else 0

            print(f"Global - Category {category}: Total Jobs = {total_jobs}, Completed Jobs = {total_completed_jobs}")
            print(f"Average Completion Time = {total_average_completion_time}")
            print(f"Average Waiting Time = {total_average_waiting_time}")

            # Append global summary data
            global_summary_data.append({
                'Category': category,
                'Total Jobs': total_jobs,
                'Completed Jobs': total_completed_jobs,
                'Average Completion Time': total_average_completion_time,
                'Average Waiting Time': total_average_waiting_time
            })

            # Extract and process time series data
            _process_and_plot_timeseries(resource_pool, category, simulation_time, interval, global_directory)

            # Plot global completion and waiting times
            _plot_times(waiting_times, completion_times, category, global_directory, simulation_time, interval)

        # Save global summary data to CSV
        global_summary_df = pd.DataFrame(global_summary_data)
        global_summary_csv_path = os.path.join(global_directory, 'global_summary_statistics.csv')
        global_summary_df.to_csv(global_summary_csv_path, index=False)
        print(f"Global summary statistics saved to {global_summary_csv_path}")


def _process_and_plot_timeseries(resource_pool, category, simulation_time, interval, subdirectory_path, site_id=None):
    """
    Processes the time series data and plots average waiting, completion, and turnaround times.
    :param resource_pool: The ResourcePool instance.
    :param category: The category ID.
    :param simulation_time: The total simulation time.
    :param interval: Time interval for binning.
    :param subdirectory_path: Directory to save the plots and CSVs.
    :param site_id: To distinguish between site-specific and global results.
    """
    # Extract data lists from the resource pool
    times = resource_pool.time_series[category]['times']
    waiting_times = resource_pool.time_series[category]['waiting_times']
    completion_times = resource_pool.time_series[category]['completion_times']

    # Ensure that times, waiting_times, and completion_times have data
    if not times or not waiting_times or not completion_times:
        print(f"No time series data available for category {category} to process.")
        return
    
    # Filter out records where completion times are None
    filtered_data = [
        (t, w, c) for t, w, c in zip(times, waiting_times, completion_times)
        if c is not None
    ]

    # Create DataFrame from filtered data if not empty
    if filtered_data:
        df = pd.DataFrame(filtered_data, columns=['times', 'waiting_times', 'completion_times'])

        # Calculate turnaround times and bin the data
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
            title_prefix = f"Site {site_id}" if site_id is not None else "Global"
            plt.title(f"Avg. Times for {title_prefix} Category {category}", fontsize=20)
            plt.xlabel('Simulation Time', fontsize=18)
            plt.ylabel('Avg. Time (s)', fontsize=18)
            plt.legend(loc='best')
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
    else:
        print(f"No data available for category {category} to process.")


def _plot_times(waiting_times, completion_times, category, output_directory, simulation_time, interval, site_id=None):
    """
    Helper function to plot waiting, completion, and turnaround times.

    :param waiting_times: List of waiting times.
    :param completion_times: List of completion times.
    :param category: Category ID.
    :param output_directory: Directory to save the plots.
    :param simulation_time: The total simulation time.
    :param interval: Time interval for binning the data.
    :param site_id: Optional site ID to include in the plot titles and legends (for site-specific results).
    """
    turnaround_times = [sum(x) for x in zip(completion_times, waiting_times)]

    # Ensure all lists are of the same length
    max_length = max(len(waiting_times), len(completion_times), len(turnaround_times))
    waiting_times.extend([None] * (max_length - len(waiting_times)))
    completion_times.extend([None] * (max_length - len(completion_times)))
    turnaround_times.extend([None] * (max_length - len(turnaround_times)))

    # Determine if this is for a specific site or global
    title_prefix = f"Site {site_id}" if site_id is not None else "Global"

    plt.figure(figsize=(20, 5))

    # Plot waiting times
    plt.subplot(131)
    plt.plot(waiting_times, 'ro-', label=f'{title_prefix} Waiting Time')
    plt.title(f'{title_prefix} Waiting Times for Category {category}', fontsize=20)
    plt.xlabel('Job Index', fontsize=18)
    plt.ylabel('Time (s)', fontsize=18)
    # plt.legend(loc='best')
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 
    plt.grid(True)

    # Plot completion times
    plt.subplot(132)
    plt.plot(completion_times, 'bo-', label=f'{title_prefix} Completion Time')
    plt.title(f'{title_prefix} Completion Times for Category {category}', fontsize=20)
    plt.xlabel('Job Index', fontsize=18)
    plt.ylabel('Time (s)', fontsize=18)
    # plt.legend(loc='best')
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 
    plt.grid(True)

    # Plot turnaround times
    plt.subplot(133)
    plt.plot(turnaround_times, 'go-', label=f'{title_prefix} Turnaround Time')
    plt.title(f'{title_prefix} Turnaround Times for Category {category}', fontsize=20)
    plt.xlabel('Job Index', fontsize=18)
    plt.ylabel('Time (s)', fontsize=18)
    # plt.legend(loc='best')
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 
    plt.grid(True)

    plt.tight_layout()

    plot_path = os.path.join(output_directory, f'Times_for_Category_{category}.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Times for Category {category} saved to {plot_path}")

    # Save data to CSV
    data = {
        'waiting_times': waiting_times,
        'completion_times': completion_times,
        'turnaround_times': turnaround_times
    }
    df = pd.DataFrame(data)
    csv_path = os.path.join(output_directory, f'Times_for_Category_{category}.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")


""" ********************** plotting faults experienced by jobs from ResourcePool ************************** """
def plot_job_failures_and_completion_times(resource_pool, output_directory):
    """
    Plots job failures and completion times, ensuring failure counts are properly incremented,
    with different colors for each job category.
    
    Parameters:
    - resource_pool: ResourcePool object containing job interruption records.
    - output_directory: Directory where the plots will be saved.
    """
    # Construct the path to the global subdirectory
    subdirectory_path = os.path.join(output_directory, 'Global_ResourcePool', 'Faults')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    job_interruption_record = resource_pool.common_job_interruption_record
    ledger = resource_pool.common_ledger

    # Extract data for plotting
    failure_times = job_interruption_record['fault_identification_time']
    job_ids = job_interruption_record['job_id']
    processor_ids = job_interruption_record['processor_id']

    # Calculate completion times for failed jobs and their categories
    completion_times = []
    categories = []
    for job_id in job_ids:
        job_completion_time = None
        job_category = None
        # Loop through the ledger to find the job's category and completion time
        for category, records in ledger.items():
            for record in records:
                if record['job_id'] == job_id:
                    job_category = category
                    job_completion_time = record.get('completion_time', None)  # Fetch completion time
                    break
            if job_category is not None:
                break
        completion_times.append(job_completion_time)
        categories.append(job_category)

    # Create a DataFrame with all the necessary data
    data = {
        'failure_times': failure_times,
        'job_ids': job_ids,
        'processor_ids': processor_ids,
        'completion_times': completion_times,
        'categories': categories
    }
    df = pd.DataFrame(data)

    # Initialize a dictionary to keep track of failure counts for each job ID
    job_failure_counts = {}

    # Update failure counts sequentially for each job ID as they fail
    failure_counts = []
    for idx, row in df.iterrows():
        job_id = row['job_ids']
        if job_id not in job_failure_counts:
            job_failure_counts[job_id] = 1
        else:
            job_failure_counts[job_id] += 1
        failure_counts.append(job_failure_counts[job_id])

    # Assign the computed failure counts back to the DataFrame
    df['failure_counts'] = failure_counts

    # Create a colormap for the categories
    unique_categories = df['categories'].unique()
    # colors = plt.cm.get_cmap('Set1', len(unique_categories))  # Use Set1 colormap for more distinct colors
    # category_color_map = {category: colors(i) for i, category in enumerate(unique_categories)}

    # Set a single color for all categories (for example, 'blue')
    fixed_color = 'red'
    category_color_map = {category: fixed_color for category in unique_categories}


    # Create figure and axes for the plot
    fig, ax = plt.subplots()

    # Group job IDs by their failure times and stack them vertically using '\n'.join()
    job_ids_by_time = df.groupby(['failure_times', 'failure_counts'])['job_ids'].apply(lambda x: '\n'.join(x.astype(str)))

    # Track which categories have been plotted for the legend
    plotted_categories = set()

    # Plot the failure counts, label the job IDs at the correct failure count position with colors for each category
    for idx, row in df.iterrows():
        color = category_color_map[row['categories']]
        label = f'Category {row["categories"]}' if row['categories'] not in plotted_categories else ""
        ax.scatter(row['failure_times'], row['failure_counts'], color=color, s=100, label=label)

        # Add the category to the plotted categories set
        plotted_categories.add(row['categories'])

        # Only label job IDs with multiple failures
        if row['failure_counts'] > 1:
            job_ids_label = job_ids_by_time[(row['failure_times'], row['failure_counts'])]
            ax.text(row['failure_times'], row['failure_counts'] + 0.1, job_ids_label, 
                    ha='center', fontsize=14, rotation=45)

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
    # Set the y-ticks as integers
    ax.set_yticks(range(0, max_failure_count + 1, 1))

    # plt.title('Number of Failures Over Time', fontsize=20)
    plt.xticks(fontsize=16)  
    plt.yticks(fontsize=16) 

    # Add legend for categories
    # ax.legend(loc="upper left", fontsize=16)

    fig.tight_layout()

    # Save the plot
    scatter_plot_file = os.path.join(subdirectory_path, 'job_failures_scatter_plot_colored.png')
    plt.savefig(scatter_plot_file)
    plt.close()
    print(f"Scatter plot saved to {scatter_plot_file}")

    # Save the complete DataFrame (including completion times) to CSV
    csv_path = os.path.join(subdirectory_path, 'job_failures_and_completion_times.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")



""" ********************** plotting for processor ************************** """
def processor_visualize_job_data(processors, directory, site_id):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    for processor in processors:
        job_times = [job.total_processing_time for job in processor.job_records]
        data_arrival_times = [job.data_arrival_time for job in processor.job_records]

        plt.figure(figsize=(14, 7))
        
        # Plot for processing times
        plt.subplot(1, 2, 1)
        plt.bar(range(len(job_times)), job_times, color='b')
        plt.title(f'Processing Times\nfor Jobs on Processor {processor.processor_id}', fontsize=20)
        plt.xlabel('Job Index', fontsize=18)
        plt.ylabel('Processing Time', fontsize=18)
        plt.xticks(range(len(job_times)), fontsize=16)  # Set X-axis from 0 to the number of jobs
        plt.yticks(fontsize=16)

        # Plot for data arrival times
        plt.subplot(1, 2, 2)
        plt.bar(range(len(data_arrival_times)), data_arrival_times, color='r')
        plt.title(f'Data Arrival Times\nfor Jobs on Processor {processor.processor_id}', fontsize=20)
        plt.xlabel('Job Index', fontsize=18)
        plt.ylabel('Data Arrival Time', fontsize=18)
        plt.xticks(range(len(data_arrival_times)), fontsize=16)  # Set X-axis from 0 to the number of jobs
        plt.yticks(fontsize=16)

        plt.tight_layout()
        plot_path = os.path.join(subdirectory_path, f'Data_Arrival_Times_for_Jobs_on_Processor_{processor.processor_id}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Data Arrival Times for Jobs on Processor {processor.processor_id} Plot saved to {plot_path}")

        # Save the data to CSV
        data = {
            'job_times': job_times,
            'data_arrival_times': data_arrival_times
        }
        df = pd.DataFrame(data)
        csv_path = os.path.join(subdirectory_path, f'Data_Arrival_Times_for_Jobs_on_Processor_{processor.processor_id}.csv')
        df.to_csv(csv_path, index=False)
        print(f"CSV saved to {csv_path}")


def processor_visualize_processor_performance(processors, directory, site_id):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    all_processing_times = [job.total_processing_time for processor in processors for job in processor.job_records]
    all_data_arrival_times = [job.data_arrival_time for processor in processors for job in processor.job_records]

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

def processor_plot_average_data_arrival_times(processors, directory, simulation_time, interval, site_id):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Initialize a plot
    plt.figure(figsize=(10, 5))

    # Iterate through each processor to collect and plot their data arrival times
    for processor in processors:
        data_points = []
        for job in processor.job_records:
            if hasattr(job, 'data_arrival_time') and job.data_arrival_time is not None:
                # Collect job request time and arrival time
                data_points.append((job.data_received_time, job.data_arrival_time))
        
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
    # plt.legend()
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

def processor_visualize_average_performance(processors, directory, site_id):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'processors')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    avg_processing_times = []
    avg_data_arrival_times = []
    processor_ids = []

    for processor in processors:
        if processor.job_records:
            avg_proc_time = sum([job.total_processing_time for job in processor.job_records]) / len(processor.job_records)
            avg_data_time = sum([job.data_arrival_time for job in processor.job_records]) / len(processor.job_records)
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
    # ax.legend()

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
def dtn_plot_data_handling_times(dtn, directory, site_id):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'dtn')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Extract data preparation times and prepare for plotting
    job_ids = []
    handling_times = []
    for job_id, times in dtn.data_preparation_times.items():
        if times['start_preparation_time'] and times['end_preparation_time']:
            duration = times['end_preparation_time'] - times['start_preparation_time']
            job_ids.append(job_id)
            handling_times.append(duration)

    if not handling_times:
        print("No data handling times to display.")
        return

    # Plotting the handling times
    plt.figure(figsize=(10, 5))
    plt.bar(job_ids, handling_times, color='blue')
    plt.title('DTN Data Handling Times', fontsize=20)
    plt.xlabel('Job ID', fontsize=18)
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
        'job_ids': job_ids,
        'handling_times': handling_times
    }
    df = pd.DataFrame(data)
    csv_path = os.path.join(subdirectory_path, 'DTN_Data_Handling_Times.csv')
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")

def dtn_plot_data_handling_time_series(dtn, directory, simulation_time, interval, site_id):
    """Plots the average DTN data preparation times over simulation time intervals."""
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'dtn')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Extract preparation times and their corresponding start times
    times = []
    preparation_durations = []
    for job_id, timings in dtn.data_preparation_times.items():
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
def router_plot_router_load(routers, aqm, directory, simulation_time, interval, site_id, filter_edge=False):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'routers')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Separate edge router and non-edge routers
    edge_router = routers[-1]  # The last router is the edge router
    non_edge_routers = routers[:-1]  # All other routers are non-edge routers

    # Plot for edge router and non-edge routers separately if filter_edge is True
    if filter_edge:
        plot_router_load([edge_router], 'Edge', aqm, simulation_time, interval, subdirectory_path)
        plot_router_load(non_edge_routers, 'in-site', aqm, simulation_time, interval, subdirectory_path)
    else:
        plot_router_load(routers, 'in-site', aqm, simulation_time, interval, subdirectory_path)

def plot_router_load(routers, router_type, aqm, simulation_time, interval, subdirectory_path):
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
            csv_path = os.path.join(subdirectory_path, f'{router_type}_Total_Queue_Load_Over_Time.csv')
            all_data.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

        plt.title(f'Total Queue Load Over Time ({router_type} Routers)', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)
        plot_path = os.path.join(subdirectory_path, f'{router_type}_Total_Queue_Load_Over_Time.png')
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
            csv_path = os.path.join(subdirectory_path, f'{router_type}_Average_Load_Over_Time.csv')
            all_avg_data.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")


        plt.title(f'Avg. Load Over Time ({router_type} Routers)', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Avg. Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)
        plot_path = os.path.join(subdirectory_path, f'{router_type}_Average_Load_Over_Time.png')
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

        plt.title(f'Total Queue Load Over Time ({router_type} Routers)', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        plot_path = os.path.join(subdirectory_path, f'{router_type}_Total_Router_Load_Over_Time.png')
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
            csv_path = os.path.join(subdirectory_path, f'{router_type}_Total_Router_Load_Over_Time.csv')
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
                csv_path = os.path.join(subdirectory_path, f'{router_type}_Average_Queue_Load_Over_Time_Router_{router.router_id}.csv')
                all_avg_data.to_csv(csv_path, index=False)
                
                print(f"CSV saved to {csv_path}")

            plt.title(f'Avg. Load Over Time for {router_type} Router {router.router_id}', fontsize=20)
            plt.xlabel('Time', fontsize=18)
            plt.ylabel('Avg. Number of Queued Packets', fontsize=18)
            # plt.legend(fontsize=16)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)  
            plt.yticks(fontsize=16) 
            plt.grid(True)

            plot_path = os.path.join(subdirectory_path, f'{router_type}_Average_Queue_Load_Over_Time_Router_{router.router_id}.png')
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
            csv_path = os.path.join(subdirectory_path, f'{router_type}_Total_Router_Load_Over_Time.csv')
            all_router_data.to_csv(csv_path, index=False)
            print(f"CSV saved to {csv_path}")

        plt.title(f'Total Queue Load Over Time ({router_type} Routers)', fontsize=20)
        plt.xlabel('Time', fontsize=18)
        plt.ylabel('Number of Queued Packets', fontsize=18)
        plt.legend(fontsize=16)
        plt.xlim([0, simulation_time])
        plt.ylim(bottom=0)
        plt.xticks(fontsize=16)  
        plt.yticks(fontsize=16) 
        plt.grid(True)

        plot_path = os.path.join(subdirectory_path, f'{router_type}_Total_Router_Load_Over_Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Total Queue Load Over Time plot saved at {plot_path}")

    else:
        raise ValueError(f'AQM Error: Unsupported AQM input "{aqm}"')

def router_calculate_and_plot_average_wait_times(routers, aqm, directory, simulation_time, interval, site_id, filter_edge=False):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'routers')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Separate edge router and non-edge routers
    edge_router = routers[-1]  # The last router is the edge router
    non_edge_routers = routers[:-1]  # All other routers are non-edge routers

    # Plot for edge router and non-edge routers separately if filter_edge is True
    if filter_edge:
        plot_router_wait_times([edge_router], 'Edge', aqm, simulation_time, interval, subdirectory_path)
        plot_router_wait_times(non_edge_routers, 'Non-Edge', aqm, simulation_time, interval, subdirectory_path)
    else:
        plot_router_wait_times(routers, 'All', aqm, simulation_time, interval, subdirectory_path)

def plot_router_wait_times(routers, router_type, aqm, simulation_time, interval, subdirectory_path):
    if aqm == 'fifo':
        plt.figure(figsize=(10, 5))

        # Initialize a flag to check if any data is available for plotting
        data_available = False

        for router in routers:
            if router.packet_wait_times:
                # Create a DataFrame for each router's packet wait times
                df = pd.DataFrame(router.packet_wait_times, columns=['time', 'wait_time'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['wait_time'].mean().reset_index()

                if not df_avg.empty:
                    data_available = True
                    time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                    plt.plot(time_bins_mid, df_avg['wait_time'], label=f'Router {router.router_id}')

        if data_available:
            plt.title(f'Avg. Packet Wait Times Over Time ({router_type} Routers)', fontsize=20)
            plt.xlabel('Time (s)', fontsize=18)
            plt.ylabel('Avg. Wait Time (s)', fontsize=18)
            plt.legend(fontsize=16)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)
            plt.grid(True)

            plot_path = os.path.join(subdirectory_path, f'{router_type}_average_wait_times.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"average_wait_times plot saved to {plot_path}")

            # Save the averaged data to CSV
            if data_available:
                avg_data = {
                    'time_bin_mid': time_bins_mid,
                    'avg_wait_time': df_avg['wait_time']
                }
                avg_df = pd.DataFrame(avg_data)
                csv_path = os.path.join(subdirectory_path, f'{router_type}_average_wait_times.csv')
                avg_df.to_csv(csv_path, index=False)
                print(f"CSV saved to {csv_path}")
        else:
            print("No wait time data available for plotting.")

    elif aqm == 'fq':
        plt.figure(figsize=(10, 5))
        data_available = False

        for router in routers:
            if router.packet_wait_times:
                df = pd.DataFrame(router.packet_wait_times, columns=['time', 'wait_time'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['wait_time'].mean().reset_index()

                if not df_avg.empty:
                    data_available = True
                    time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                    plt.plot(time_bins_mid, df_avg['wait_time'], label=f'Router {router.router_id}')

        if data_available:
            plt.title(f'Avg. Packet Wait Times Over Time ({router_type} Routers)', fontsize=20)
            plt.xlabel('Time (s)', fontsize=18)
            plt.ylabel('Avg. Wait Time (s)', fontsize=18)
            plt.legend(fontsize=16)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.grid(True)
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)

            plot_path = os.path.join(subdirectory_path, f'{router_type}_average_wait_times.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"average_wait_times plot saved to {plot_path}")

            # Save the averaged data to CSV
            if data_available:
                avg_data = {
                    'time_bin_mid': time_bins_mid,
                    'avg_wait_time': df_avg['wait_time']
                }
                avg_df = pd.DataFrame(avg_data)
                csv_path = os.path.join(subdirectory_path, f'{router_type}_average_wait_times.csv')
                avg_df.to_csv(csv_path, index=False)
                print(f"CSV saved to {csv_path}")
        else:
            print("No wait time data available for plotting.")
        
    else:
        raise ValueError(f'AQM Error: Unsupported AQM input "{aqm}"')




"""*********************** visualization function - for TCP connections ****************************"""

def plot_tcp_metrics(tcp_connections, directory, simulation_time, interval, site_id, filter_dtn=False):
    # Construct the path to the subdirectory for this site
    subdirectory_path = os.path.join(directory, f'Site_{site_id}', 'TCP_Metrics')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)

    # Filter connections relevant to this site
    site_relevant_connections = []
    for conn in tcp_connections:
        # Include connection if either source or destination involves this site
        src_site_id = getattr(conn.src, 'dtn_id', getattr(conn.src, 'processor_id', None))
        dst_site_id = getattr(conn.dst, 'dtn_id', getattr(conn.dst, 'processor_id', None))
        
        # For DTN connections, check if DTN belongs to this site (simplified by DTN ID mod 4 for dumbell)
        if isinstance(conn.src, DTN):
            src_site_id = conn.src.dtn_id
        if isinstance(conn.dst, DTN):
            dst_site_id = conn.dst.dtn_id
            
        # Include connection if it involves this site
        if (isinstance(conn.src, DTN) and conn.src.dtn_id == site_id) or \
           (isinstance(conn.dst, DTN) and conn.dst.dtn_id == site_id) or \
           (hasattr(conn.src, 'processor_id') and conn.src.processor_id // 3 == site_id) or \
           (hasattr(conn.dst, 'processor_id') and conn.dst.processor_id // 3 == site_id):
            site_relevant_connections.append(conn)

    # Separate DTN-DTN connections if filter_dtn is True
    dtn_tcp_connections = []
    non_dtn_tcp_connections = []

    if filter_dtn:
        for conn in site_relevant_connections:
            if isinstance(conn.src, DTN) and isinstance(conn.dst, DTN):
                dtn_tcp_connections.append(conn)
            else:
                non_dtn_tcp_connections.append(conn)
    else:
        non_dtn_tcp_connections = site_relevant_connections

    # Plot for DTN-DTN connections separately if filter_dtn is True
    if filter_dtn:
        plot_connections(dtn_tcp_connections, 'inter-site', simulation_time, interval, subdirectory_path)
        plot_connections(non_dtn_tcp_connections, 'intra-site', simulation_time, interval, subdirectory_path)
    else:
        plot_connections(non_dtn_tcp_connections, 'intra-site', simulation_time, interval, subdirectory_path)


def plot_connections(connections, connection_type, simulation_time, interval, subdirectory_path):
    # Define the metrics to plot
    metrics = ['cwnd', 'rtt', 'throughput', 'goodput', 'retransmissions']
    for metric in metrics:
        y_label = ''  # Initialize y_label

        plt.figure(figsize=(10, 5))

        # DataFrame to store individual connection data for saving to CSV
        combined_df = pd.DataFrame()

        # Plot individual connection metrics
        for connection in connections:
            df = pd.DataFrame()  # Initialize df
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

            # Save individual connection data to CSV
            if not df.empty:
                df['connection_id'] = connection.connection_id  # Add connection_id to the DataFrame
                combined_df = pd.concat([combined_df, df])  # Combine all connection data

                plt.plot(df['time'], df[metric], label=f'Connection {connection.connection_id}')

        # Save combined DataFrame for individual connections to CSV
        if not combined_df.empty:
            individual_csv_path = os.path.join(subdirectory_path, f'{metric}_{connection_type}_individual_connections.csv')
            combined_df.to_csv(individual_csv_path, index=False)
            print(f"Individual connection data for {metric} saved to {individual_csv_path}")

        # Only proceed with plotting if there is data
        if y_label != '' and not combined_df.empty:
            plt.title(f'{metric.capitalize()} Over Time for {connection_type} Connections', fontsize=20)
            plt.xlabel('Time (s)', fontsize=18)
            plt.ylabel(y_label, fontsize=18)
            plt.grid(True)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)
            plot_path = os.path.join(subdirectory_path, f'{metric}_{connection_type}_connections.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"{metric.capitalize()} Over Time for {connection_type} Connections plot saved to {plot_path}")

        # Plot aggregate metrics
        aggregate_df = pd.DataFrame()
        for connection in connections:
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

            # Save aggregate data to CSV
            aggregate_csv_path = os.path.join(subdirectory_path, f'average_{metric}_{connection_type}_over_time.csv')
            avg_data.to_csv(aggregate_csv_path, index=False)
            print(f"Aggregate data for {metric} saved to {aggregate_csv_path}")

            plt.figure(figsize=(10, 5))
            if metric == 'retransmissions':
                plt.bar(avg_data['time_bin_mid'], avg_data[metric], color='blue')
            else:
                plt.plot(avg_data['time_bin_mid'], avg_data[metric], marker='o', linestyle='-', color='blue')
            plt.title(f'Avg. {metric.capitalize()} Over Time Across All {connection_type} Connections', fontsize=20)
            plt.xlabel('Time (s)', fontsize=18)
            plt.ylabel(y_label, fontsize=18)
            plt.grid(True)
            plt.xlim([0, simulation_time])
            plt.ylim(bottom=0)
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)
            plot_path = os.path.join(subdirectory_path, f'average_{metric}_{connection_type}_over_time.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"Avg. {metric.capitalize()} Over Time Across All {connection_type} Connections plot saved to {plot_path}")


def plot_combined_cwnd_dumbell(tcp_connections_per_site, directory, simulation_time, time_range=None):
    """
    Plot combined CWND behavior for both inter-site connections in dumbell topology.
    Shows both TCP connections competing through the bottleneck on the same chart.
    
    :param tcp_connections_per_site: Dictionary of TCP connections per site
    :param directory: Base directory to save plots and CSVs
    :param simulation_time: Total simulation time
    :param time_range: Optional tuple (start_time, end_time) for custom time range
    """
    import shutil
    
    # Create combined analysis directory
    combined_dir = os.path.join(directory, 'Combined_Analysis')
    if not os.path.exists(combined_dir):
        os.makedirs(combined_dir)
    
    # Collect all inter-site DTN-to-DTN connections with CWND data
    all_inter_site_connections = []
    
    for site_id, connections in tcp_connections_per_site.items():
        for conn in connections:
            # Check if this is an inter-site DTN-to-DTN connection with CWND data
            if (isinstance(conn.src, DTN) and isinstance(conn.dst, DTN) and 
                hasattr(conn, 'cwnd_log') and not conn.cwnd_log.empty):
                
                connection_data = {
                    'site_id': site_id,
                    'connection_id': conn.connection_id,
                    'src_site': getattr(conn.src, 'dtn_id', 'unknown'),
                    'dst_site': getattr(conn.dst, 'dtn_id', 'unknown'),
                    'cwnd_data': conn.cwnd_log,
                    'connection': conn
                }
                all_inter_site_connections.append(connection_data)
    
    if len(all_inter_site_connections) < 2:
        print("Warning: Less than 2 inter-site connections found for combined CWND plotting")
        return
    
    # Create combined CSV
    csv_data = []
    csv_headers = ['time', 'cwnd', 'connection_id', 'job', 'src_site', 'dst_site']
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    markers = ['o', 's', '^', 'D', 'v']
    
    # Track completion times to determine x-axis limit
    completion_times = []
    
    for idx, conn_data in enumerate(all_inter_site_connections[:5]):  # Limit to 5 connections
        cwnd_df = conn_data['cwnd_data']
        times = cwnd_df['time'].tolist()
        cwnd_values = cwnd_df['cwnd'].tolist()
        
        # Filter by time range if specified
        if time_range:
            start_time, end_time = time_range
            filtered_data = [(t, c) for t, c in zip(times, cwnd_values) if start_time <= t <= end_time]
            if filtered_data:
                times, cwnd_values = zip(*filtered_data)
            else:
                continue
        
        # Track completion time (last data point)
        if times:
            completion_times.append(max(times))
        
        # Plot the connection
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        label = f"Job {idx} (Site {conn_data['src_site']}→Site {conn_data['dst_site']}, Conn {conn_data['connection_id']})"
        
        plt.plot(times, cwnd_values, 
                label=label,
                linewidth=2, 
                color=color, 
                marker=marker, 
                markersize=2,
                alpha=0.8)
        
        # Add to CSV data
        for time, cwnd in zip(times, cwnd_values):
            csv_data.append([
                time, cwnd, conn_data['connection_id'], 
                f"Job{idx}", f"Site{conn_data['src_site']}", f"Site{conn_data['dst_site']}"
            ])
    
    # Determine x-axis limit
    if time_range:
        x_lim_right = time_range[1]  # Use specified end time
    else:
        x_lim_right = simulation_time  # Use passed simulation_time (which is max completion time)
    
    # Customize the plot
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('CWND (Congestion Window)', fontsize=12)
    plt.title('TCP CWND Comparison: Simultaneous Jobs in Dumbell Topology\n(Competing connections through bottleneck)', 
              fontsize=14, pad=20)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xlim(left=0, right=x_lim_right)  # Use consistent x-axis limit
    plt.ylim(bottom=0)
    
    # Save the plot
    if time_range:
        plot_path = os.path.join(combined_dir, f'combined_cwnd_dumbell_topology_{time_range[0]}_to_{time_range[1]}s.png')
        csv_path = os.path.join(combined_dir, f'combined_cwnd_dumbell_data_{time_range[0]}_to_{time_range[1]}s.csv')
    else:
        plot_path = os.path.join(combined_dir, 'combined_cwnd_dumbell_topology.png')
        csv_path = os.path.join(combined_dir, 'combined_cwnd_dumbell_data.csv')
    
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Combined CWND plot saved to: {plot_path}")
    
    # Save the CSV
    df = pd.DataFrame(csv_data, columns=csv_headers)
    df.to_csv(csv_path, index=False)
    print(f"Combined CWND CSV saved to: {csv_path}")
    
    # Print summary statistics
    print("\n=== COMBINED CWND ANALYSIS ===")
    for idx, conn_data in enumerate(all_inter_site_connections):
        cwnd_df = conn_data['cwnd_data']
        if not cwnd_df.empty:
            cwnd_values = cwnd_df['cwnd'].tolist()
            times = cwnd_df['time'].tolist()
            print(f"Job {idx} (Connection {conn_data['connection_id']}):")
            print(f"  Start CWND: {cwnd_values[0]:.1f}")
            print(f"  Max CWND: {max(cwnd_values):.1f}")
            print(f"  Final CWND: {cwnd_values[-1]:.1f}")
            print(f"  Completion Time: {times[-1]:.1f}s")
            print(f"  Data points: {len(cwnd_values)}")
    
    return plot_path, csv_path


def plot_combined_throughput_dumbell(tcp_connections_per_site, directory, simulation_time, time_range=None):
    """
    Plot combined throughput behavior for both inter-site connections in dumbell topology.
    Shows both TCP connections competing through the bottleneck on the same chart.
    
    :param tcp_connections_per_site: Dictionary of TCP connections per site
    :param directory: Base directory to save plots and CSVs
    :param simulation_time: Total simulation time
    :param time_range: Optional tuple (start_time, end_time) for custom time range
    """
    import shutil
    
    # Create combined analysis directory
    combined_dir = os.path.join(directory, 'Combined_Analysis')
    if not os.path.exists(combined_dir):
        os.makedirs(combined_dir)
    
    # Collect all inter-site DTN-to-DTN connections with meaningful throughput data
    all_inter_site_connections = []
    from entities.dtn import DTN # Import DTN here to avoid circular dependency
    
    for site_id, connections in tcp_connections_per_site.items():
        for conn in connections:
            # Check if this is an inter-site DTN-to-DTN connection and has meaningful throughput data
            if (isinstance(conn.src, DTN) and isinstance(conn.dst, DTN) and 
                hasattr(conn, 'throughput_log') and not conn.throughput_log.empty and 
                conn.throughput_log['throughput'].max() > 0):
                
                connection_data = {
                    'site_id': site_id,
                    'connection_id': conn.connection_id,
                    'src_site': getattr(conn.src, 'dtn_id', 'unknown'),
                    'dst_site': getattr(conn.dst, 'dtn_id', 'unknown'),
                    'throughput_data': conn.throughput_log,
                    'connection': conn
                }
                all_inter_site_connections.append(connection_data)
    
    if len(all_inter_site_connections) < 2:
        print("Warning: Less than 2 inter-site connections found for combined throughput plotting")
        return
    
    # Create combined CSV
    csv_data = []
    csv_headers = ['time', 'throughput', 'connection_id', 'job', 'src_site', 'dst_site']
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    markers = ['o', 's', '^', 'D', 'v']
    
    # Track completion times to determine x-axis limit
    completion_times = []
    
    for idx, conn_data in enumerate(all_inter_site_connections[:5]):  # Limit to 5 connections
        throughput_df = conn_data['throughput_data']
        times = throughput_df['time'].tolist()
        throughput_values = throughput_df['throughput'].tolist()
        
        # Filter by time range if specified
        if time_range:
            start_time, end_time = time_range
            filtered_data = [(t, th) for t, th in zip(times, throughput_values) if start_time <= t <= end_time]
            if filtered_data:
                times, throughput_values = zip(*filtered_data)
            else:
                continue
        
        # Track completion time (last data point)
        if times:
            completion_times.append(max(times))
        
        # Plot the connection
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        label = f"Job {idx} (Site {conn_data['src_site']}→Site {conn_data['dst_site']}, Conn {conn_data['connection_id']})"
        
        plt.plot(times, throughput_values, 
                label=label,
                linewidth=2, 
                color=color, 
                marker=marker, 
                markersize=2,
                alpha=0.8)
        
        # Add to CSV data
        for time, throughput in zip(times, throughput_values):
            csv_data.append([
                time, throughput, conn_data['connection_id'], 
                f"Job{idx}", f"Site{conn_data['src_site']}", f"Site{conn_data['dst_site']}"
            ])
    
    # Determine x-axis limit
    if time_range:
        x_lim_right = time_range[1]  # Use specified end time
    else:
        x_lim_right = simulation_time  # Use passed simulation_time (which is max completion time)
    
    # Customize the plot
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Throughput (bytes/second)', fontsize=12)
    plt.title('TCP Throughput Comparison: Simultaneous Jobs in Dumbell Topology\n(Competing connections through bottleneck)', 
              fontsize=14, pad=20)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xlim(left=0, right=x_lim_right)  # Use consistent x-axis limit
    plt.ylim(bottom=0)
    
    # Save the plot
    if time_range:
        plot_path = os.path.join(combined_dir, f'combined_throughput_dumbell_topology_{time_range[0]}_to_{time_range[1]}s.png')
        csv_path = os.path.join(combined_dir, f'combined_throughput_dumbell_data_{time_range[0]}_to_{time_range[1]}s.csv')
    else:
        plot_path = os.path.join(combined_dir, 'combined_throughput_dumbell_topology.png')
        csv_path = os.path.join(combined_dir, 'combined_throughput_dumbell_data.csv')
    
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Combined throughput plot saved to: {plot_path}")
    
    # Save the CSV
    df = pd.DataFrame(csv_data, columns=csv_headers)
    df.to_csv(csv_path, index=False)
    print(f"Combined throughput CSV saved to: {csv_path}")
    
    # Print summary statistics
    print("\n=== COMBINED THROUGHPUT ANALYSIS ===")
    for idx, conn_data in enumerate(all_inter_site_connections):
        throughput_df = conn_data['throughput_data']
        if not throughput_df.empty:
            throughput_values = throughput_df['throughput'].tolist()
            times = throughput_df['time'].tolist()
            print(f"Job {idx} (Connection {conn_data['connection_id']}):")
            print(f"  Start Throughput: {throughput_values[0]:.1f} bytes/s")
            print(f"  Max Throughput: {max(throughput_values):.1f} bytes/s")
            print(f"  Final Throughput: {throughput_values[-1]:.1f} bytes/s")
            print(f"  Average Throughput: {sum(throughput_values)/len(throughput_values):.1f} bytes/s")
            print(f"  Completion Time: {times[-1]:.1f}s")
            print(f"  Data points: {len(throughput_values)}")
    
    return plot_path, csv_path


def plot_combined_retransmissions_dumbell(tcp_connections_per_site, directory, simulation_time, time_range=None):
    """
    Plot combined retransmission behavior for both inter-site connections in dumbell topology.
    Creates both a summary bar chart and a time-based stacked bar chart showing retransmission events.
    
    :param tcp_connections_per_site: Dictionary of TCP connections per site
    :param directory: Base directory to save plots and CSVs
    :param simulation_time: Total simulation time
    :param time_range: Optional tuple (start_time, end_time) for custom time range
    """
    import shutil
    
    # Create combined analysis directory
    combined_dir = os.path.join(directory, 'Combined_Analysis')
    if not os.path.exists(combined_dir):
        os.makedirs(combined_dir)
    
    # Collect all inter-site DTN-to-DTN connections (same filtering as CWND plot)
    all_inter_site_connections = []
    
    for site_id, connections in tcp_connections_per_site.items():
        for conn in connections:
            # Check if this is an inter-site DTN-to-DTN connection with CWND data (same as CWND plot)
            if (isinstance(conn.src, DTN) and isinstance(conn.dst, DTN) and 
                hasattr(conn, 'cwnd_log') and not conn.cwnd_log.empty):
                
                # Include all connections that have CWND data, even if they have no retransmission data
                if hasattr(conn, 'retransmission_log') and not conn.retransmission_log.empty:
                    retransmission_values = conn.retransmission_log['retransmissions'].tolist()
                    total_retransmissions = sum(1 for x in retransmission_values if x == -1)  # Count retransmission events
                    retransmission_data = conn.retransmission_log
                else:
                    total_retransmissions = 0
                    retransmission_data = pd.DataFrame(columns=['time', 'retransmissions']) # Empty DataFrame
                
                connection_data = {
                    'site_id': site_id,
                    'connection_id': conn.connection_id,
                    'src_site': getattr(conn.src, 'dtn_id', 'unknown'),
                    'dst_site': getattr(conn.dst, 'dtn_id', 'unknown'),
                    'total_retransmissions': total_retransmissions,
                    'retransmission_data': retransmission_data, # Store the DataFrame
                    'connection': conn
                }
                all_inter_site_connections.append(connection_data)
    
    if len(all_inter_site_connections) < 1:
        print("Warning: Less than 1 inter-site connections found for combined retransmission plotting")
        return
    
    # Create combined CSV
    csv_data = []
    csv_headers = ['connection_id', 'job', 'src_site', 'dst_site', 'total_retransmissions']
    
    # Define colors for plotting
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    
    # Prepare data for bar chart
    connection_labels = []
    retransmission_counts = []
    bar_colors = []
    
    for idx, conn_data in enumerate(all_inter_site_connections[:5]):  # Limit to 5 connections
        # Create labels with proper line breaks (not escaped \n)
        connection_labels.append(f"Job {idx}\n(Site {conn_data['src_site']}→Site {conn_data['dst_site']}\nConn {conn_data['connection_id']})")
        retransmission_counts.append(conn_data['total_retransmissions'])
        bar_colors.append(colors[idx % len(colors)])
        
        # Add to CSV data
        csv_data.append([
            conn_data['connection_id'], 
            f"Job{idx}", 
            f"Site{conn_data['src_site']}", 
            f"Site{conn_data['dst_site']}", 
            conn_data['total_retransmissions']
        ])
    
    # Create bar chart
    plt.figure(figsize=(10, 6))
    bars = plt.bar(connection_labels, retransmission_counts, color=bar_colors, alpha=0.8)
    
    # Add value labels on top of bars
    for bar, count in zip(bars, retransmission_counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + max(1, height * 0.05),
                f'{count}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Customize the plot
    plt.xlabel('Connection', fontsize=12)
    plt.ylabel('Total Retransmissions', fontsize=12)
    plt.title('TCP Retransmission Comparison: Simultaneous Jobs in Dumbell Topology\n(Competing connections through bottleneck)', 
              fontsize=14, pad=20)
    plt.xticks(rotation=0, ha='center')
    plt.grid(True, alpha=0.3, axis='y')
    plt.ylim(bottom=0, top=max(retransmission_counts) * 1.2 if retransmission_counts else 10)
    
    # Save the plot
    if time_range:
        plot_path = os.path.join(combined_dir, f'combined_retransmissions_dumbell_topology_{time_range[0]}_to_{time_range[1]}s.png')
        csv_path = os.path.join(combined_dir, f'combined_retransmissions_dumbell_data_{time_range[0]}_to_{time_range[1]}s.csv')
    else:
        plot_path = os.path.join(combined_dir, 'combined_retransmissions_dumbell_topology.png')
        csv_path = os.path.join(combined_dir, 'combined_retransmissions_dumbell_data.csv')
    
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Combined retransmissions bar chart saved to: {plot_path}")
    
    # Save the CSV
    df = pd.DataFrame(csv_data, columns=csv_headers)
    df.to_csv(csv_path, index=False)
    print(f"Combined retransmissions CSV saved to: {csv_path}")
    
    # Now create the time-based stacked plot
    plt.figure(figsize=(12, 8))
    
    # Collect retransmission events by time
    time_data = {}
    job_names = [f"Job {idx}" for idx in range(len(all_inter_site_connections[:5]))]
    
    for idx, conn_data in enumerate(all_inter_site_connections[:5]):
        job_name = f"Job {idx}"
        if hasattr(conn_data['connection'], 'retransmission_log') and not conn_data['connection'].retransmission_log.empty:
            retransmission_df = conn_data['connection'].retransmission_log
            times = retransmission_df['time'].tolist()
            retransmission_values = retransmission_df['retransmissions'].tolist()
            
            # Find retransmission events (value == -1)
            for time, value in zip(times, retransmission_values):
                if value == -1:  # Retransmission event
                    if time not in time_data:
                        time_data[time] = {}
                    time_data[time][job_name] = time_data[time].get(job_name, 0) + 1
    
    # Aggregate by second (round timestamps to nearest second)
    aggregated_time_data = {}
    for time, jobs in time_data.items():
        second = round(time)  # Round to nearest second
        if second not in aggregated_time_data:
            aggregated_time_data[second] = {}
        for job, count in jobs.items():
            aggregated_time_data[second][job] = aggregated_time_data[second].get(job, 0) + count
    
    # Get all unique seconds and sort them
    all_seconds = sorted(aggregated_time_data.keys()) if aggregated_time_data else []
    
    # Filter by time range if specified
    if time_range:
        start_time, end_time = time_range
        all_seconds = [s for s in all_seconds if start_time <= s <= end_time]
    
    if not all_seconds:
        print("Warning: No retransmission events found in the specified time range")
        return
    
    # Prepare data for stacked bar chart
    bar_data = {job: [] for job in job_names}
    
    for second in all_seconds:
        for job in job_names:
            bar_data[job].append(aggregated_time_data[second].get(job, 0))
    
    # Plot stacked bars - show all jobs even if they have 0 retransmissions
    bottom_values = [0] * len(all_seconds)  # Track the bottom for stacking
    
    for idx, job in enumerate(job_names):
        conn_data = all_inter_site_connections[idx]
        label = f"Job {idx} (Site {conn_data['src_site']}→Site {conn_data['dst_site']}, Conn {conn_data['connection_id']})"
        
        # Get the data for this job
        job_data = bar_data[job]
        
        # Plot this job's bars on top of the previous ones
        plt.bar(all_seconds, job_data, bottom=bottom_values, 
               label=label, color=colors[idx % len(colors)], alpha=0.8, width=0.8)
        
        # Update bottom values for the next job
        for i in range(len(all_seconds)):
            bottom_values[i] += job_data[i]
    
    # Add individual job numbers on their respective stacked bars
    for second_idx, second in enumerate(all_seconds):
        bottom = 0
        for job in job_names:
            job_count = aggregated_time_data[second].get(job, 0)
            if job_count > 0:  # Only add text if this job has retransmissions
                # Position text in the middle of this job's stacked bar segment
                text_position = bottom + (job_count / 2)
                plt.text(second, text_position, str(job_count), 
                        ha='center', va='center', fontsize=9, fontweight='bold',
                        color='white')  # White text for better visibility
            bottom += job_count
    
    # Determine x-axis limit
    if time_range:
        x_lim_right = time_range[1]  # Use specified end time
    else:
        x_lim_right = simulation_time  # Use passed simulation_time (which is max completion time)
    
    # Customize the plot
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Retransmission Events (count)', fontsize=12)
    plt.title('TCP Retransmission Events Over Time: Simultaneous Jobs in Dumbell Topology\n(Competing connections through bottleneck)', 
              fontsize=14, pad=20)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3, axis='y')
    plt.xlim(left=0, right=x_lim_right)  # Use consistent x-axis limit
    plt.ylim(bottom=0)
    
    # Save the time-based plot
    if time_range:
        time_plot_path = os.path.join(combined_dir, f'combined_retransmissions_time_dumbell_topology_{time_range[0]}_to_{time_range[1]}s.png')
        time_csv_path = os.path.join(combined_dir, f'combined_retransmissions_time_dumbell_data_{time_range[0]}_to_{time_range[1]}s.csv')
    else:
        time_plot_path = os.path.join(combined_dir, 'combined_retransmissions_time_dumbell_topology.png')
        time_csv_path = os.path.join(combined_dir, 'combined_retransmissions_time_dumbell_data.csv')
    
    plt.savefig(time_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Combined retransmissions time-based plot saved to: {time_plot_path}")
    
    # Save the time-based CSV
    time_csv_data = []
    time_csv_headers = ['time', 'job', 'retransmission_count']
    
    for second in all_seconds:
        for job in job_names:
            count = aggregated_time_data[second].get(job, 0)
            if count > 0:  # Only include actual retransmission events
                time_csv_data.append([second, job, count])
    
    time_df = pd.DataFrame(time_csv_data, columns=time_csv_headers)
    time_df.to_csv(time_csv_path, index=False)
    print(f"Combined retransmissions time-based CSV saved to: {time_csv_path}")

def plot_combined_rtt_dumbell(tcp_connections_per_site, directory, simulation_time, time_range=None):
    """
    Plot combined RTT behavior for both inter-site connections in dumbell topology.
    Shows both TCP connections competing through the bottleneck on the same chart.
    
    :param tcp_connections_per_site: Dictionary of TCP connections per site
    :param directory: Base directory to save plots and CSVs
    :param simulation_time: Total simulation time
    :param time_range: Optional tuple (start_time, end_time) for custom time range
    """
    import shutil
    
    # Create combined analysis directory
    combined_dir = os.path.join(directory, 'Combined_Analysis')
    if not os.path.exists(combined_dir):
        os.makedirs(combined_dir)
    
    # Collect all inter-site DTN-to-DTN connections
    all_inter_site_connections = []
    
    for site_id, connections in tcp_connections_per_site.items():
        for conn in connections:
            # Check if this is an inter-site DTN-to-DTN connection
            if (isinstance(conn.src, DTN) and isinstance(conn.dst, DTN) and 
                hasattr(conn, 'rtt_log') and not conn.rtt_log.empty):
                
                # Include all connections with RTT data, even if they have no RTT events
                rtt_values = conn.rtt_log['rtt'].tolist()
                # Include all connections that have RTT logs, regardless of RTT count
                connection_data = {
                    'site_id': site_id,
                    'connection_id': conn.connection_id,
                    'src_site': getattr(conn.src, 'dtn_id', 'unknown'),
                    'dst_site': getattr(conn.dst, 'dtn_id', 'unknown'),
                    'rtt_data': conn.rtt_log,
                    'connection': conn
                }
                all_inter_site_connections.append(connection_data)
    
    if len(all_inter_site_connections) < 2:
        print("Warning: Less than 2 inter-site connections found for combined RTT plotting")
        return
    
    # Create combined CSV
    csv_data = []
    csv_headers = ['time', 'rtt', 'connection_id', 'job', 'src_site', 'dst_site']
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    markers = ['o', 's', '^', 'D', 'v']
    
    # Track completion times to determine x-axis limit
    completion_times = []
    
    for idx, conn_data in enumerate(all_inter_site_connections[:5]):  # Limit to 5 connections
        rtt_df = conn_data['rtt_data']
        times = rtt_df['time'].tolist()
        rtt_values = rtt_df['rtt'].tolist()
        
        # Filter by time range if specified
        if time_range:
            start_time, end_time = time_range
            filtered_data = [(t, r) for t, r in zip(times, rtt_values) if start_time <= t <= end_time]
            if filtered_data:
                times, rtt_values = zip(*filtered_data)
            else:
                continue
        
        # Track completion time (last data point)
        if times:
            completion_times.append(max(times))
        
        # Plot the connection
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        label = f"Job {idx} (Site {conn_data['src_site']}→Site {conn_data['dst_site']}, Conn {conn_data['connection_id']})"
        
        plt.plot(times, rtt_values, 
                label=label,
                linewidth=2, 
                color=color, 
                marker=marker, 
                markersize=2,
                alpha=0.8)
        
        # Add to CSV data
        for time, rtt in zip(times, rtt_values):
            csv_data.append([
                time, rtt, conn_data['connection_id'], 
                f"Job{idx}", f"Site{conn_data['src_site']}", f"Site{conn_data['dst_site']}"
            ])
    
    # Determine x-axis limit
    if time_range:
        x_lim_right = time_range[1]  # Use specified end time
    else:
        x_lim_right = simulation_time  # Use passed simulation_time (which is max completion time)
    
    # Customize the plot
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('RTT (seconds)', fontsize=12)
    plt.title('TCP RTT Comparison: Simultaneous Jobs in Dumbell Topology\n(Competing connections through bottleneck)', 
              fontsize=14, pad=20)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xlim(left=0, right=x_lim_right)  # Use consistent x-axis limit
    plt.ylim(bottom=0)
    
    # Save the plot
    if time_range:
        plot_path = os.path.join(combined_dir, f'combined_rtt_dumbell_topology_{time_range[0]}_to_{time_range[1]}s.png')
        csv_path = os.path.join(combined_dir, f'combined_rtt_dumbell_data_{time_range[0]}_to_{time_range[1]}s.csv')
    else:
        plot_path = os.path.join(combined_dir, 'combined_rtt_dumbell_topology.png')
        csv_path = os.path.join(combined_dir, 'combined_rtt_dumbell_data.csv')
    
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Combined RTT plot saved to: {plot_path}")
    
    # Save the CSV
    df = pd.DataFrame(csv_data, columns=csv_headers)
    df.to_csv(csv_path, index=False)
    print(f"Combined RTT CSV saved to: {csv_path}")
    
    # Print summary statistics
    print("\n=== COMBINED RTT ANALYSIS ===")
    for idx, conn_data in enumerate(all_inter_site_connections):
        rtt_df = conn_data['rtt_data']
        if not rtt_df.empty:
            rtt_values = rtt_df['rtt'].tolist()
            times = rtt_df['time'].tolist()
            print(f"Job {idx} (Connection {conn_data['connection_id']}):")
            print(f"  Start RTT: {rtt_values[0]:.3f}s")
            print(f"  Max RTT: {max(rtt_values):.3f}s")
            print(f"  Final RTT: {rtt_values[-1]:.3f}s")
            print(f"  Average RTT: {sum(rtt_values)/len(rtt_values):.3f}s")
            print(f"  Completion Time: {times[-1]:.1f}s")
            print(f"  Data points: {len(rtt_values)}")
    
    return plot_path, csv_path
