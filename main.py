import argparse
import os
import pandas as pd
import simpy
import random
from entities.dtn import DTN
from entities.resourcepool import ResourcePool
from protocols.tcp import TCPConnection
from utils.helpers import *
from visualization.plotting import *
import traceback

def _default_task_category_profiles():
    return {
        0: {'type': 'computation-heavy', 'mean_comp': 1000, 'max_comp': 3000, 'mean_data': 50, 'max_data': 500},
        1: {'type': 'data-heavy', 'mean_comp': 600, 'max_comp': 1800, 'mean_data': 200, 'max_data': 700},
        2: {'type': 'extreme-heavy-gpu', 'mean_comp': 1600, 'max_comp': 4800, 'mean_data': 350, 'max_data': 1000}
        # Add more profiles for other categories as needed
    }

def _default_category_profiles():
    return {
        0: {'type': 'computation-heavy', 'compute_speed': 500, 'nic_speed': 1000, 'max_concurrent_tasks': 10},
        1: {'type': 'data-heavy', 'compute_speed': 300, 'nic_speed': 10000, 'max_concurrent_tasks': 20},
        2: {'type': 'extreme-heavy-gpu', 'compute_speed': 800, 'nic_speed': 20000, 'max_concurrent_tasks': 10}
        # Add more profiles for other categories as needed
    }

def _load_csv(fn):
    df = pd.read_csv(fn)
    return {i: row.to_dict() for i, row in df.iterrows()}

def generate_failure_schedule(number_of_processors, random_seed, number_of_outputs, simulation_time, max_failure_duration):
    random.seed(random_seed)
    data = {
        'processor_id': [random.randint(0, number_of_processors - 1) for _ in range(number_of_outputs)],
        'failure_time': [random.uniform(0, simulation_time) for _ in range(number_of_outputs)],
        'failure_duration': [random.uniform(0, max_failure_duration) for _ in range(number_of_outputs)]
    }
    df = pd.DataFrame(data)
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--processors-per-category', type=int, default=3)
    parser.add_argument('--router-nic-speed', type=int, default=25000, help='similar or equivalent to Router_NIC_speed in Mbps')
    parser.add_argument('--aqm', choices=['fq', 'fifo'], default='fifo')
    parser.add_argument('--router-queue-size', type=int, default=1000)
    parser.add_argument('--cca', choices=['reno', 'cubic', 'htcp'], default='htcp')
    parser.add_argument('--link-delay', type=float, default=0.001, help='adding delay as an one-way-delay to simulate link travel time, added at router')
    parser.add_argument('--processor-task-lookup-time', type=float, default=0.5, help='time a processor will wait before checking for new task in the resource pool')
    parser.add_argument('--dtn-nic-speed', type=int, default=50000)
    parser.add_argument('--simulation-time', type=int, default=200)
    parser.add_argument('--average-interval', type=int, default=1)
    parser.add_argument('--random-seed', type=int, default=1)
    parser.add_argument('--processor-category-profiles')
    parser.add_argument('--task-category-profiles')
    parser.add_argument('--task-replay-log')
    parser.add_argument('--task-generator', choices=['random', 'replay', 'replay_with_fault'], default='random')
    parser.add_argument('--number-of-failures', type=int, default=10)
    parser.add_argument('--max-failure-duration', type=float, default=10.0)
    parser.add_argument('--failure-schedule-file', type=str, help='CSV file containing the failure schedule')
    args = parser.parse_args()

    base_directory = os.path.join(os.path.dirname(__file__), 'runs')
    # Ensure the directory exists
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)

    processor_category_profiles = _load_csv(args.processor_category_profiles) if args.processor_category_profiles else _default_category_profiles()
    env = simpy.Environment()
    num_categories = len(processor_category_profiles)
    
    # Generate or load failure schedule
    number_of_processors = num_categories * args.processors_per_category
    if args.task_generator == 'replay_with_fault' and args.failure_schedule_file:
        failure_schedule_df = pd.read_csv(args.failure_schedule_file)
    else:
        failure_schedule_df = generate_failure_schedule(number_of_processors, args.random_seed, args.number_of_failures, args.simulation_time, args.max_failure_duration)

    # Convert the failure schedule to a dictionary
    failure_schedule = {}
    for _, row in failure_schedule_df.iterrows():
        processor_id = row['processor_id']
        if processor_id not in failure_schedule:
            failure_schedule[processor_id] = {'failure_times': [], 'failure_durations': []}
        failure_schedule[processor_id]['failure_times'].append(row['failure_time'])
        failure_schedule[processor_id]['failure_durations'].append(row['failure_duration'])

    # Combine the base directory with the new directory name to form the full path
    directory = os.path.join(base_directory, str(args.random_seed))

    resource_pool = ResourcePool(env, num_categories)
    pheromone_map = create_pheromone_map(num_categories, args.processors_per_category)

    routers = create_network(env, num_categories, args.router_nic_speed, args.link_delay, args.router_queue_size, args.aqm)

    # List to store all TCP connections
    tcp_connections = []

    dtn = DTN(env, routers, args.dtn_nic_speed, tcp_connections, args.cca)

    processors = connect_processors_to_routers(env, num_categories, args.processors_per_category, resource_pool, dtn, args.processor_task_lookup_time, pheromone_map, routers, processor_category_profiles, failure_schedule, tcp_connections, args.cca)

    connect_routers_and_processors(routers, processors)

    # After setting up the network:
    verify_connections(routers)  # Optional: Verify connections to ensure all are as expected

    # Start the task generator process
    if args.task_generator == 'replay' or args.task_generator == 'replay_with_fault':
        env.process(task_replay(env, resource_pool, args.task_replay_log))
    else:
        task_category_profiles = _load_csv(args.task_category_profiles) if args.task_category_profiles else _default_task_category_profiles()
        env.process(task_generator(env, resource_pool, num_categories, task_category_profiles, args.random_seed))

    # Run simulation
    try:
        env.run(until=args.simulation_time)
        print("Simulation complete.")
    except Exception as e:
        traceback.print_exc() 

    # Visualization and summarization calls
    resource_pool_plot_results(resource_pool, directory, args.simulation_time, args.average_interval)
    # Visualization and summarization calls
    plot_task_failures_and_completion_times(resource_pool, directory) 
            
    processor_visualize_task_data(processors, directory)
    processor_visualize_processor_performance(processors, directory)
    processor_plot_average_data_arrival_times(processors, directory, args.simulation_time, args.average_interval)
    processor_visualize_average_performance(processors, directory)

    dtn_plot_data_handling_time_series(dtn, directory, args.simulation_time, args.average_interval)
    dtn_plot_data_handling_times(dtn, directory)

    plot_tcp_metrics(tcp_connections, directory, args.simulation_time, args.average_interval)

    router_plot_router_load(routers, args.aqm, directory, args.simulation_time, args.average_interval)
    router_calculate_and_plot_average_wait_times(routers, args.aqm, directory, args.simulation_time, args.average_interval)


if __name__ == "__main__":
    main()
