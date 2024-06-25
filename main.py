import os
import simpy
from entities.dtn import DTN
from entities.resourcepool import ResourcePool
from utils.helpers import *
from visualization.plotting import *
import traceback

# Initialize the SimPy Environment
env = simpy.Environment()

def main():
    base_directory = "D:\\LBL\\SWARM\\network_simulation_local\\runs"
    # Ensure the directory exists
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)

    task_category_profiles = {
        0: {'type': 'computation-heavy', 'mean_comp': 1000, 'max_comp': 3000, 'mean_data': 500, 'max_data': 5000},
        1: {'type': 'data-heavy', 'mean_comp': 600, 'max_comp': 1800, 'mean_data': 5000, 'max_data': 50000},
        2: {'type': 'extreme-heavy-gpu', 'mean_comp': 1600, 'max_comp': 4800, 'mean_data': 10000, 'max_data': 100000}
        # Add more profiles for other categories as needed
    }

    processor_category_profiles = {
        0: {'type': 'computation-heavy', 'compute_speed': 500, 'nic_speed': 1000, 'max_concurrent_tasks': 10},
        1: {'type': 'data-heavy', 'compute_speed': 300, 'nic_speed': 10000, 'max_concurrent_tasks': 20},
        2: {'type': 'extreme-heavy-gpu', 'compute_speed': 800, 'nic_speed': 20000, 'max_concurrent_tasks': 10}
        # Add more profiles for other categories as needed
    }

    env = simpy.Environment()
    num_categories = 3  # Example: 3 categories
    processors_per_category = 3
    router_nic_speed = 25000 # similar or equivalent to Router_NIC_speed in Mbps
    link_delay = 0.001   # adding delay as an one-way-delay to simulate link travel time, added at router
    dtn_nic_speed = 50000    # Mbps
    processor_task_lookup_time = 0.5    # time a processor will wait before checking for new task in the resource pool
    aqm = 'fq'    # can be 'fifo' or 'fq'
    
    simulation_time = 1000
    average_interval = 20
    random_seed_for_task_generator = 3
    
    # Combine the base directory with the new directory name to form the full path
    directory = os.path.join(base_directory, str(random_seed_for_task_generator))

    resource_pool = ResourcePool(env, num_categories)
    pheromone_map = create_pheromone_map(num_categories, processors_per_category)

    routers = create_network(env, num_categories, router_nic_speed, link_delay, aqm)

    dtn = DTN(env, routers, dtn_nic_speed)

    processors = connect_processors_to_routers(env, num_categories, processors_per_category, resource_pool, dtn, processor_task_lookup_time, pheromone_map, routers, processor_category_profiles)

    connect_routers_and_processors(routers, processors)

    # After setting up the network:
    verify_connections(routers)  # Optional: Verify connections to ensure all are as expected

    # Start the task generator process
    env.process(task_generator(env, resource_pool, num_categories, task_category_profiles, random_seed_for_task_generator))

    # Run simylation
    try:
        env.run(until=simulation_time)
        print("Simulation complete.")
    except Exception as e:
        traceback.print_exc() 

    # Visualization and summarization calls

    resource_pool_plot_results(resource_pool, directory, simulation_time, average_interval)
            
    processor_visualize_task_data(processors, directory)
    processor_visualize_processor_performance(processors, directory)
    processor_plot_average_data_arrival_times(processors, directory, simulation_time, average_interval)
    processor_visualize_average_performance(processors, directory)

    dtn_plot_data_handling_time_series(dtn, directory, simulation_time, average_interval)
    dtn_plot_data_handling_times(dtn, directory)

    router_plot_router_load(routers, aqm, directory, simulation_time, average_interval)
    router_calculate_and_plot_average_wait_times(routers, aqm, directory, simulation_time, average_interval)

if __name__ == "__main__":
    main()