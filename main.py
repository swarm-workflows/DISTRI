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

def _default_job_category_profiles():
    return {
        0: {'type': 'computation-heavy', 'mean_comp': 1000, 'max_comp': 3000, 'mean_data': 50, 'max_data': 150},
        1: {'type': 'data-heavy', 'mean_comp': 600, 'max_comp': 1800, 'mean_data': 150, 'max_data': 250},
        2: {'type': 'extreme-heavy-gpu', 'mean_comp': 1600, 'max_comp': 4800, 'mean_data': 250, 'max_data': 350}
        # Add more profiles for other categories as needed
    }

def _default_category_profiles():
    return {
        0: {'type': 'computation-heavy', 'compute_speed': 500, 'nic_speed': 500, 'max_concurrent_jobs': 10},
        1: {'type': 'data-heavy', 'compute_speed': 300, 'nic_speed': 1000, 'max_concurrent_jobs': 20},
        2: {'type': 'extreme-heavy-gpu', 'compute_speed': 800, 'nic_speed': 2000, 'max_concurrent_jobs': 10}
        # Add more profiles for other categories as needed
    }

def _load_csv(fn):
    df = pd.read_csv(fn)
    return {i: row.to_dict() for i, row in df.iterrows()}


def generate_failure_schedule(number_of_processors, random_seed, number_of_outputs, simulation_time, max_failure_duration, num_sites):
    random.seed(random_seed)
    
    failures_per_site = number_of_outputs // num_sites  # Failures evenly distributed per site
    remaining_failures = number_of_outputs % num_sites  # Any extra failures to distribute
    
    data = {'processor_id': [], 'failure_time': [], 'failure_duration': []}
    
    print(f"Total number of processors: {number_of_processors}")
    print(f"Number of failures: {number_of_outputs}")
    print(f"Failures per site: {failures_per_site}, Remaining failures: {remaining_failures}\n")

    for site_id in range(num_sites):
        num_failures_for_site = failures_per_site + (1 if site_id < remaining_failures else 0)  # Distribute remaining failures
        site_processors = range(site_id * (number_of_processors // num_sites), (site_id + 1) * (number_of_processors // num_sites))

        print(f"Site {site_id} has {num_failures_for_site} failures to assign.")
        print(f"Processors available for site {site_id}: {list(site_processors)}")

        for _ in range(num_failures_for_site):
            processor_id = random.choice(site_processors)
            failure_time = random.uniform(0, simulation_time)
            failure_duration = random.uniform(0, max_failure_duration)
            
            data['processor_id'].append(processor_id)
            data['failure_time'].append(failure_time)
            data['failure_duration'].append(failure_duration)
            
            print(f"Assigned failure to Processor {processor_id} at time {failure_time:.2f} for duration {failure_duration:.2f}")
    
    print("\nFailure schedule generated successfully.\n")
    df = pd.DataFrame(data)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--processors-per-category', type=int, default=3)
    parser.add_argument('--router-nic-speed', type=int, default=10000, help='Router NIC speed in Mbps')
    parser.add_argument('--router-queue-size', type=int, default=250)
    parser.add_argument('--edge-router-nic-speed', type=int, default=20000, help='Edge Router NIC speed in Mbps')  # New argument
    parser.add_argument('--edge-router-queue-size', type=int, default=500, help='Edge Router Queue size')  # New argument
    parser.add_argument('--edge-router-delay', type=float, default=0.01, help='Edge Router Link Delay')  # New argument
    parser.add_argument('--aqm', choices=['fq', 'fifo'], default='fifo')
    parser.add_argument('--cca', choices=['reno', 'cubic', 'htcp'], default='cubic')
    parser.add_argument('--link-delay', type=float, default=0.0001, help='Link travel time as one-way-delay')
    parser.add_argument('--processor-job-lookup-time', type=float, default=0.5, help='Time before processor checks for a new job')
    parser.add_argument('--dtn-nic-speed', type=int, default=50000)
    parser.add_argument('--simulation-time', type=int, default=200)
    parser.add_argument('--average-interval', type=int, default=1)
    parser.add_argument('--random-seed', type=int, default=1)
    parser.add_argument('--processor-category-profiles')
    parser.add_argument('--job-category-profiles')
    parser.add_argument('--job-replay-log')
    parser.add_argument('--job-generator', choices=['random', 'replay', 'replay_with_fault'], default='random')
    parser.add_argument('--number-of-failures', type=int, default=9)
    parser.add_argument('--max-failure-duration', type=float, default=10.0)
    parser.add_argument('--failure-schedule-file', type=str, help='CSV file containing the failure schedule')
    parser.add_argument('--num-sites', type=int, default=3, help='Number of HPC sites to simulate')
    parser.add_argument('--add-edge-router', type=lambda x: x.lower() == 'true', default=True, help='Should we connect all the HPC sites or not')
    parser.add_argument('--dtn-data-request', type=lambda x: x.lower() == 'true', default=True, help='Should DTNs request data from other DTNs or not: should be true when "add_edge_router" is true')
    args = parser.parse_args()

    base_directory = os.path.join(os.path.dirname(__file__), 'runs')
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)

    processor_category_profiles = _load_csv(args.processor_category_profiles) if args.processor_category_profiles else _default_category_profiles()

        
    random.seed(args.random_seed)
    np.random.seed(args.random_seed)


    env = simpy.Environment()
    num_categories = len(processor_category_profiles)

    # Generate or load failure schedule
    number_of_processors = num_categories * args.processors_per_category * args.num_sites  # Multiply by number of sites
    if args.job_generator == 'replay_with_fault' and args.failure_schedule_file:
        failure_schedule_df = pd.read_csv(args.failure_schedule_file)
    else:
        failure_schedule_df = generate_failure_schedule(number_of_processors, args.random_seed, args.number_of_failures, args.simulation_time, args.max_failure_duration, args.num_sites)

    # Convert the failure schedule to a dictionary
    failure_schedule = {}
    for _, row in failure_schedule_df.iterrows():
        processor_id = row['processor_id']
        if processor_id not in failure_schedule:
            failure_schedule[processor_id] = {'failure_times': [], 'failure_durations': []}
        failure_schedule[processor_id]['failure_times'].append(row['failure_time'])
        failure_schedule[processor_id]['failure_durations'].append(row['failure_duration'])

    directory = os.path.join(base_directory, str(args.random_seed))


    # Create containers for DTNs and edge routers if necessary
    dtns = []
    edge_routers = []
    dtns_per_site = {}
    routers_per_site = {}
    processors_per_site = {}
    resource_pools_per_site = {}
    tcp_connections_per_site = {}

    # Create multiple HPC sites in a loop
    for site_id in range(args.num_sites):
        print(f"Creating HPC site {site_id} out of 0 to {args.num_sites - 1}")

        # Each site has its own resource pool, pheromone map, routers, and processors
        resource_pool = ResourcePool(env, num_categories)
        resource_pools_per_site[site_id] = resource_pool
        
        pheromone_map = create_pheromone_map(num_categories, args.processors_per_category)

        # Create routers for the site, and include an edge router if add_edge_router is True
        routers = create_network(env, num_categories, args.router_nic_speed, args.link_delay, args.router_queue_size, args.aqm, add_edge_router=args.add_edge_router)
        routers_per_site[site_id] = routers

        # List to store TCP connections specific to this site
        tcp_connections = []

        if args.add_edge_router:
            # The last router in the list is the dedicated edge router, now using different NIC speed, queue size, and delay
            edge_router = routers[-1]
            edge_router.nic_speed = args.edge_router_nic_speed  # Set the custom NIC speed
            edge_router.queue_limit = args.edge_router_queue_size  # Set the custom queue size
            edge_router.delay = args.edge_router_delay  # Set the custom delay
            edge_routers.append(edge_router)

            # Create DTN for the site and connect it to the dedicated edge router
            dtn = DTN(env, routers, args.dtn_nic_speed, tcp_connections, args.cca, args.dtn_data_request)
            dtns.append(dtn)
            dtns_per_site[site_id] = dtn

            # Create processors for the site and connect them to intra-site routers (not the edge router)
            processors = connect_processors_to_routers(env, num_categories, args.processors_per_category, resource_pool, dtn, args.processor_job_lookup_time, pheromone_map, routers[:-1], processor_category_profiles, failure_schedule, tcp_connections, args.cca)
            processors_per_site[site_id] = processors

            # Connect intra-site routers and processors (excluding edge router)
            connect_routers_and_processors(routers[:-1], processors)

            # After setting up the network:
            verify_connections(routers[:-1])  # Verify intra-site connections (excluding edge router)

        else:
            # Create DTN for the site with all routers (no edge router in this case)
            dtn = DTN(env, routers, args.dtn_nic_speed, tcp_connections, args.cca, args.dtn_data_request)
            dtns.append(dtn)
            dtns_per_site[site_id] = dtn

            # Create processors for the site and connect them to all routers
            processors = connect_processors_to_routers(env, num_categories, args.processors_per_category, resource_pool, dtn, args.processor_job_lookup_time, pheromone_map, routers, processor_category_profiles, failure_schedule, tcp_connections, args.cca)
            processors_per_site[site_id] = processors
            
            # Connect all routers and processors
            connect_routers_and_processors(routers, processors)

            # Verify connections for all routers
            verify_connections(routers)

        # Start job generation or replay based on user input
        if args.job_generator == 'replay' or args.job_generator == 'replay_with_fault':
            env.process(job_replay(env, resource_pool, args.job_replay_log))
        else:
            job_category_profiles = _load_csv(args.job_category_profiles) if args.job_category_profiles else _default_job_category_profiles()
            env.process(job_generator(env, resource_pool, num_categories, job_category_profiles, args.random_seed))

        # Store the site's TCP connections
        tcp_connections_per_site[site_id] = tcp_connections


    # After creating all sites, if edge routers are being used, connect DTNs to edge routers and establish mesh connections
    if args.add_edge_router:
        connect_dtns_and_edge_routers(dtns, edge_routers)
        # Verify connections for edge routers
        verify_connections(edge_routers)
        # Assign the list of all DTNs to each DTN
        for dtn in dtns:
            dtn.set_dtn_list(dtns)  # Set the list of all DTNs for inter-DTN data requests

    # Run simulation
    try:
        env.run(until=args.simulation_time)
        print("Simulation complete.")
    except Exception as e:
        traceback.print_exc()

    # Visualization and summarization calls for each site could be handled similarly to the original implementation
    plot_job_failures_and_completion_times(resource_pools_per_site[0], directory)
    
    for site_id in range(args.num_sites):
        print(f"Plotting for HPC site {site_id} out of 0 to {args.num_sites - 1}")
        
        # Create resource pools, routers, processors, etc., for each site
        ...

        resource_pool = resource_pools_per_site[site_id]
        routers = routers_per_site[site_id]
        processors = processors_per_site[site_id]
        tcp_connections = tcp_connections_per_site[site_id]

        # After running the simulation for each site, generate the plots
        resource_pool_plot_results(resource_pool, directory, args.simulation_time, args.average_interval, site_id)
        processor_visualize_job_data(processors, directory, site_id)
        dtn_plot_data_handling_times(dtn, directory, site_id)
        router_plot_router_load(routers, args.aqm, directory, args.simulation_time, args.average_interval, site_id, args.add_edge_router)
        plot_tcp_metrics(tcp_connections, directory, args.simulation_time, args.average_interval, site_id, args.add_edge_router)
        processor_visualize_processor_performance(processors, directory, site_id)
        processor_plot_average_data_arrival_times(processors, directory, args.simulation_time, args.average_interval, site_id)
        processor_visualize_average_performance(processors, directory, site_id)
        dtn_plot_data_handling_time_series(dtn, directory, args.simulation_time, args.average_interval, site_id)
        router_calculate_and_plot_average_wait_times(routers, args.aqm, directory, args.simulation_time, args.average_interval, site_id, args.add_edge_router)

if __name__ == "__main__":
    main()
