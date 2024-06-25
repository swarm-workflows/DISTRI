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


    """Calculate and print summary statistics for each category, and plot task times."""
    for category in resource_pool.ledger:
        tasks = resource_pool.ledger[category]
        completed_tasks = [t for t in tasks if t['completion_time'] is not None]
        waiting_times = [t['waiting_time'] for t in tasks if t['waiting_time'] is not None]
        completion_times = [t['completion_time'] for t in completed_tasks if t['completion_time']]

        total_tasks = len(tasks)
        total_average_completion_time = np.mean(completion_times) if completion_times else 0
        total_average_waiting_time = np.mean(waiting_times) if waiting_times else 0

        print(f"Category {category}: Total Tasks = {total_tasks}, Completed Tasks = {len(completed_tasks)}")
        print(f"  Average Completion Time = {total_average_completion_time}")
        print(f"  Average Waiting Time = {total_average_waiting_time}")


        # Plot completion and waiting times
        plt.figure(figsize=(15, 5))
        plt.subplot(131)
        plt.plot(waiting_times, 'ro-', label='Waiting Time')
        plt.title(f'Waiting Times for Category {category} (includes unfinished tasks)')
        plt.xlabel('Task Index')
        plt.ylabel('Time (s)')
        plt.grid(True)

        plt.subplot(132)
        plt.plot(completion_times, 'bo-', label='Completion Time')
        plt.title(f'Completion Times for Category {category}')
        plt.xlabel('Task Index')
        plt.ylabel('Time (s)')
        plt.grid(True)

        total_completion_times = [sum(x) for x in zip(completion_times, waiting_times)]
        plt.subplot(133)
        plt.plot(total_completion_times, 'go-', label='Total Completion Time')
        plt.title(f'Total Completion Times for Category {category}')
        plt.xlabel('Task Index')
        plt.ylabel('Time (s)')
        plt.grid(True)

        plt.tight_layout()
        # plt.show()

        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, f'Completion and Waiting Times for Category {category}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Completion and Waiting Time Plot saved to {plot_path}")

    
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
            df['total_completion_time'] = df['waiting_times'] + df['completion_times']
            df['time_bin'] = pd.cut(df['times'], bins=np.arange(0, simulation_time + interval, interval), right=False)
            avg_data = df.groupby('time_bin', observed=True)[['waiting_times', 'completion_times', 'total_completion_time']].mean()

            # Plotting only the bins with data
            if not avg_data.empty:
                mid_points = [interval.left + (interval.right - interval.left) / 2 for interval in avg_data.index]
                plt.figure(figsize=(12, 6))
                plt.plot(mid_points, avg_data['waiting_times'], label='Average Waiting Time', marker='o')
                plt.plot(mid_points, avg_data['completion_times'], label='Average Completion Time', marker='x')
                plt.plot(mid_points, avg_data['total_completion_time'], label='Total Completion Time', marker='s')
                plt.title(f"Average Times for Category {category} Over Simulation Time")
                plt.xlabel('Simulation Time')
                plt.ylabel('Average Time (s)')
                plt.legend()
                plt.grid(True)
                plt.xlim([0, simulation_time])
                # plt.show()

                # Save the plot to the specified directory
                plot_path = os.path.join(subdirectory_path, f'Average Times for Category {category} Over Simulation Time.png')
                plt.savefig(plot_path)
                plt.close()
                print(f"Average Times for Category {category} Plot saved to {plot_path}")
            else:
                print(f"No data available for plotting in category {category}.")




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
        plt.subplot(1, 2, 1)
        plt.bar(range(len(task_times)), task_times, color='b')
        plt.title(f'Processing Times for Tasks on Processor {processor.processor_id}')
        plt.xlabel('Task Index')
        plt.ylabel('Processing Time')

        plt.subplot(1, 2, 2)
        plt.bar(range(len(data_arrival_times)), data_arrival_times, color='r')
        plt.title(f'Data Arrival Times for Tasks on Processor {processor.processor_id}')
        plt.xlabel('Task Index')
        plt.ylabel('Data Arrival Time')

        plt.tight_layout()
        # plt.show()
        
        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, f'Data Arrival Times for Tasks on Processor {processor.processor_id}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Data Arrival Times for Tasks on Processor {processor.processor_id} Plot saved to {plot_path}")


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
    plt.title('Distribution of Processing Times Across All Processors')
    plt.xlabel('Processing Time')
    plt.ylabel('Frequency')

    plt.subplot(1, 2, 2)
    plt.hist(all_data_arrival_times, bins=20, color='red', alpha=0.7)
    plt.title('Distribution of Data Arrival Times Across All Processors')
    plt.xlabel('Data Arrival Time')
    plt.ylabel('Frequency')

    plt.tight_layout()
    # plt.show()

    # Save the plot to the specified directory
    plot_path = os.path.join(subdirectory_path, 'Distribution of Data Arrival Times Across All Processors.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Distribution of Data Arrival Times Across All Processors Plot saved to {plot_path}")


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

    plt.title(f'Average Data Arrival Time per {interval} Unit Time Intervals')
    plt.xlabel('Simulation Time (s)')
    plt.ylabel('Average Data Arrival Time (s)')
    plt.legend()
    plt.grid(True)
    plt.xlim([0, simulation_time])  # Ensure x-axis covers the full simulation time

    # Save the plot to the specified directory
    plot_path = os.path.join(subdirectory_path, 'average_data_arrival_times.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"average_data_arrival_times Plot saved to {plot_path}")



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

        plt.title(f'Category {category}: Average Data Arrival Time per {interval} Unit Time Intervals')
        plt.xlabel('Simulation Time (s)')
        plt.ylabel('Average Data Arrival Time (s)')
        plt.legend()
        plt.grid(True)
        plt.xlim([0, simulation_time])  # Ensure x-axis covers the full simulation time

        # Save the plot to the specified directory for each category
        plot_path = os.path.join(subdirectory_path, f'average_data_arrival_times_category_{category}.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Average Data Arrival Times plot for Category {category} saved to {plot_path}")


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

    ind = np.arange(len(processors))  # the x locations for the groups
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.bar(ind - width/2, avg_processing_times, width, label='Avg Processing Time')
    rects2 = ax.bar(ind + width/2, avg_data_arrival_times, width, label='Avg Data Arrival Time')

    ax.set_xlabel('Processor ID')
    ax.set_ylabel('Time (s)')
    ax.set_title('Average Processing and Data Arrival Times by Processor')
    ax.set_xticks(ind)
    ax.set_xticklabels(processor_ids)
    ax.legend()

    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)

    fig.tight_layout()
    # plt.show()
    # Save the plot to the specified directory
    plot_path = os.path.join(subdirectory_path, 'Average Processing and Data Arrival Times by Processor.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Average Processing and Data Arrival Times by Processor plot saved to {plot_path}")





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
    plt.title('DTN Data Handling Times')
    plt.xlabel('Task ID')
    plt.ylabel('Data Handling Time (seconds)')
    plt.grid(True)

    # Save the plot to the specified directory
    plot_path = os.path.join(subdirectory_path, 'DTN Data Handling Times.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"DTN Data Handling Times by DTN plot saved to {plot_path}")


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
    plt.title(f'Average DTN Data Handling Time per {interval} Unit Time Intervals')
    plt.xlabel('Simulation Time (s)')
    plt.ylabel('Average Data Handling Time (Seconds)')
    plt.grid(True)
    plt.xlim([0, simulation_time])  # Ensure x-axis covers the full simulation time
    # plt.show()

    # Save the plot to the specified directory
    plot_path = os.path.join(subdirectory_path, f'Average DTN Data Handling Time per {interval} Unit Time Intervals.png')
    plt.savefig(plot_path)
    plt.close()
    print(f"Average DTN Data Handling Time per {interval} Unit Time Intervals by DTN plot saved to {plot_path}")


"""*********************** visualization function - for routers ****************************"""

def router_plot_router_load(routers, aqm, directory, simulation_time, interval):
    # Construct the path to the subdirectory
    subdirectory_path = os.path.join(directory, 'routers')

    # Ensure the subdirectory exists
    if not os.path.exists(subdirectory_path):
        os.makedirs(subdirectory_path)


    if aqm == 'fifo':
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.load_history:
                times, loads = zip(*router.load_history)
                plt.plot(times, loads, label=f'Router {router.router_id}')
        plt.title('Queue Load Over Time')
        plt.xlabel('Time')
        plt.ylabel('Number of Queued Packets')
        plt.legend()
        plt.grid(True)
        # plt.show()
        
        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, 'Queue Load Over Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Queue Load Over Time {plot_path}")
        
        # # Plot load for each egress queue within each router
        # for router in routers:
        #     plt.figure(figsize=(10, 5))
        #     for queue_id, queue in router.queues.items():
        #         if router.egress_load_history:
        #             times, loads = zip(*[(time, load) for time, q_id, load in router.egress_load_history if q_id == queue_id])
        #             plt.plot(times, loads, label=f'Queue {queue_id}')
            
        #     plt.title(f'Egress Queue Load Over Time for Router {router.router_id}')
        #     plt.xlabel('Time')
        #     plt.ylabel('Number of Queued Packets')
        #     plt.legend()
        #     plt.grid(True)

        #     # Save the plot to the specified directory
        #     plot_path = os.path.join(subdirectory_path, f'Router {router.router_id} Egress Queue Load Over Time.png')
        #     plt.savefig(plot_path)
        #     plt.close()
        #     print(f"Saved individual queue load plot for Router {router.router_id} to {plot_path}")

        # print(f"Total and individual load plots saved in {subdirectory_path}")

        # Plotting average ingress load for all routers
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.load_history:
                df = pd.DataFrame(router.load_history, columns=['time', 'load'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['load'].mean().reset_index()
                time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                plt.plot(time_bins_mid, df_avg['load'], label=f'Router {router.router_id}')

        plt.title('Average Load Over Time')
        plt.xlabel('Time')
        plt.ylabel('Average Number of Queued Packets')
        plt.legend()
        plt.grid(True)
        plot_path = os.path.join(subdirectory_path, 'Average Load Over Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Average Load Over Time plot saved at {plot_path}")

        # # Plotting average egress load for all routers, separate figure for each router
        # for router in routers:
        #     plt.figure(figsize=(10, 5))
        #     for queue_id in router.queues.keys():
        #         queue_loads = [(time, load) for time, q_id, load in router.egress_load_history if q_id == queue_id]
        #         if queue_loads:
        #             df = pd.DataFrame(queue_loads, columns=['time', 'load'])
        #             df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
        #             df_avg = df.groupby('time_bin', observed=True)['load'].mean().reset_index()
        #             time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
        #             plt.plot(time_bins_mid, df_avg['load'], label=f'Queue {queue_id}')

        #     plt.title(f'Average Egress Load Over Time for Router {router.router_id}')
        #     plt.xlabel('Time')
        #     plt.ylabel('Average Number of Queued Packets')
        #     plt.legend()
        #     plt.grid(True)
        #     plot_path = os.path.join(subdirectory_path, f'Average Egress Load Over Time Router {router.router_id}.png')
        #     plt.savefig(plot_path)
        #     plt.close()
        #     print(f"Average Egress Load Over Time plot for Router {router.router_id} saved at {plot_path}")

        print(f"All plots saved in {subdirectory_path}")

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

        plt.title('Total Router Load Over Time')
        plt.xlabel('Time')
        plt.ylabel('Total Number of Queued Packets Across All Queues')
        plt.legend()
        plt.grid(True)

        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, 'Total Router Load Over Time.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"'Total Router Load Over Time.png' {plot_path}")

        # Plot load for each queue within each router
        for router in routers:
            plt.figure(figsize=(10, 5))
            for queue_id, queue in router.queues.items():
                if router.load_history:
                    times, loads = zip(*[(time, load) for time, q_id, load in router.load_history if q_id == queue_id])
                    plt.plot(times, loads, label=f'Queue {queue_id}')
            
            plt.title(f'Load Over Time for Router {router.router_id}')
            plt.xlabel('Time')
            plt.ylabel('Number of Queued Packets')
            plt.legend()
            plt.grid(True)

            # Save the plot to the specified directory
            plot_path = os.path.join(subdirectory_path, f'Router {router.router_id} Load Over Time.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"Saved individual queue load plot for Router {router.router_id} to {plot_path}")

        # Plot average load for each queue within each router
        for router in routers:
            plt.figure(figsize=(10, 5))
            for queue_id in router.queues.keys():
                queue_loads = [(time, load) for time, q_id, load in router.load_history if q_id == queue_id]
                if queue_loads:
                    df = pd.DataFrame(queue_loads, columns=['time', 'load'])
                    df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                    df_avg = df.groupby('time_bin', observed=True)['load'].mean().reset_index()
                    time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                    plt.plot(time_bins_mid, df_avg['load'], label=f'Queue {queue_id}')

            plt.title(f'Average Queue Load Over Time for Router {router.router_id}')
            plt.xlabel('Time')
            plt.ylabel('Average Number of Queued Packets')
            plt.legend()
            plt.grid(True)

            # Save the plot to the specified directory
            plot_path = os.path.join(subdirectory_path, f'Average Queue Load Over Time Router {router.router_id}.png')
            plt.savefig(plot_path)
            plt.close()
            print(f"Average Queue Load Over Time plot for Router {router.router_id} saved at {plot_path}")

        # Plot total average load over time for all routers
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.load_history:
                df = pd.DataFrame(router.load_history, columns=['time', 'queue_id', 'load'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['load'].sum().reset_index()
                time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                plt.plot(time_bins_mid, df_avg['load'], label=f'Router {router.router_id}')

        plt.title('Total Average Load Over Time for All Routers')
        plt.xlabel('Time')
        plt.ylabel('Total Average Number of Queued Packets')
        plt.legend()
        plt.grid(True)

        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, 'Total Average Load Over Time for All Routers.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"Total Average Load Over Time for All Routers plot saved at {plot_path}")

    else:
        raise ValueError('AQM Error: Unsupported AQM input "{}"'.format(aqm))



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

        plt.title('Average Packet Wait Times Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Average Wait Time (s)')
        plt.legend()
        plt.grid(True)
        plt.xlim([0, simulation_time])  # Ensure x-axis covers the full simulation time

        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, 'average_wait_times.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"average_wait_times {plot_path}")

    elif aqm == 'fq':
        plt.figure(figsize=(10, 5))
        for router in routers:
            if router.packet_wait_times:
                df = pd.DataFrame(router.packet_wait_times, columns=['time', 'wait_time'])
                df['time_bin'] = pd.cut(df['time'], bins=range(0, simulation_time + interval, interval), right=False)
                df_avg = df.groupby('time_bin', observed=True)['wait_time'].mean().reset_index()

                time_bins_mid = df_avg['time_bin'].apply(lambda x: x.left + (x.right - x.left) / 2)
                plt.plot(time_bins_mid, df_avg['wait_time'], label=f'Router {router.router_id}')

        plt.title('Average Packet Wait Times Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Average Wait Time (s)')
        plt.legend()
        plt.grid(True)
        plt.xlim([0, simulation_time])  # Ensure x-axis covers the full simulation time

        # Save the plot to the specified directory
        plot_path = os.path.join(subdirectory_path, 'average_wait_times.png')
        plt.savefig(plot_path)
        plt.close()
        print(f"average_wait_times {plot_path}")
        
    else:
        raise ValueError('AQM Error: Unsupported AQM input "{}"'.format(aqm))