import pandas as pd
import simpy
import random
from entities.job import Job
from entities.processor import Processor
from entities.router_fifo import *
from entities.router_fq import *
import itertools  # To generate unique IDs

# Global job ID counter
global_job_id = itertools.count(0)  # This will give a unique ID to each job created across all pools.

def job_generator(env, resource_pool, num_categories, category_profiles, seed=None):
    # Seed the random number generator for reproducibility
    if seed is not None:
        random.seed(seed)

    global global_job_id  # Use the global job ID counter
    
    while True:
        category = random.randint(0, num_categories - 1)
        profile = category_profiles[category]

        # Adjusted job property generation based on category profile
        computation = random.randint(profile['mean_comp'], profile['max_comp'])
        data_volume = random.randint(profile['mean_data'], profile['max_data'])

        # Fetch a globally unique job ID
        job_id = next(global_job_id)

        # Create and add a new job to the resource pool
        job = Job(env, job_id, computation, data_volume, category)
        resource_pool.add_job(job)  # Add the job to the pool

        print(f"Generated and added job {job.id} in category {job.category} to ResourcePool {resource_pool.resource_pool_id} with comp {computation} and vol {data_volume}. Total jobs now: {len(resource_pool.common_pool[job.category].items)}")

        # Wait before generating the next job
        yield env.timeout(random.uniform(1.3, 2.5))  # New jobs are generated every 0.1 - 1.0 time units


def job_replay(env, resource_pool, log_file):
    df = pd.read_csv(log_file)
    for i, row in df.iterrows():
        job = Job(env, i, row.computation, row.data, row.category)
        resource_pool.add_job(job)
        yield env.timeout(random.uniform(1.3, 2.5))


# def create_pheromone_map(num_categories, processors_per_category):
#     pheromone_map = {category: {} for category in range(num_categories)}
#     for category in range(num_categories):
#         min_in_category = category * processors_per_category
#         max_in_category = (category + 1) * processors_per_category
#         for processor_id in range(min_in_category, max_in_category):
#             pheromone_map[category][processor_id] = 0  # Initialize pheromone levels using unique processor ID
#     return pheromone_map
    
def create_pheromone_map(num_categories, processors_per_category):
    """Initialize the pheromone map with a dictionary for each category and an entry for each processor."""
    pheromone_map = {}
    for category in range(num_categories):
        pheromone_map[category] = {}
        for processor_id in range(processors_per_category):
            # Initialize each processor with a default load value (e.g., 0)
            pheromone_map[category][processor_id] = 0
    return pheromone_map


def connect_routers_and_processors(routers, processors):
    # Establish inter-router routes for reaching remote processors
    for router in routers:
        for other_router in routers:
            if router != other_router:
                router.add_route(other_router)  # Allows routing through other routers

    # Example static route setup for processors across routers
    for router in routers:
        for processor in processors:
            if processor.router != router:
                # Route to this processor via its router
                router.add_route(processor, via=processor.router)


# Define a global router ID counter
global_router_id = 0  # This should be defined outside the function (e.g., at the top of your script)

def create_network(env, num_categories, nic_speed, delay, queue_limit, aqm, add_edge_router=True):
    """
    Create a network of routers for intra-site communication and optionally add a dedicated edge router.

    :param env: The simulation environment.
    :param num_categories: Number of categories (one router per category).
    :param nic_speed: Router NIC speed in Mbps.
    :param delay: Link delay in seconds.
    :param queue_limit: Maximum number of packets in the queue.
    :param aqm: Active queue management type ('fifo' or 'fq').
    :param add_edge_router: Whether to add an extra edge router for each site.
    :return: A list of routers (including the edge router if requested).
    """
    global global_router_id  # Reference the global router ID counter

    routers = []
    
    # Create a router for each category with a unique router_id
    for _ in range(num_categories):
        if aqm == 'fifo':
            router = RouterFifo(env, global_router_id, nic_speed, delay, queue_limit)
        elif aqm == 'fq':
            router = RouterFq(env, global_router_id, nic_speed, delay, queue_limit)
        else:
            raise ValueError(f'AQM Error: Unsupported AQM input "{aqm}"')
        
        routers.append(router)
        global_router_id += 1  # Increment the global router ID counter

    if add_edge_router:
        # Create a dedicated edge router
        if aqm == 'fifo':
            edge_router = RouterFifo(env, global_router_id, nic_speed, delay, queue_limit)
        elif aqm == 'fq':
            edge_router = RouterFq(env, global_router_id, nic_speed, delay, queue_limit)
        else:
            raise ValueError(f'AQM Error: Unsupported AQM input for edge_router "{aqm}"')

        routers.append(edge_router)  # Add edge router to the list
        print(f"Edge router added with ID {global_router_id}")
        global_router_id += 1  # Increment the global router ID counter after creating the edge router

    return routers

# Define a global processor ID counter
global_processor_id = 0  # This should be defined outside the function (e.g., at the top of your script)

def connect_processors_to_routers(env, num_categories, processors_per_category, resource_pool, dtn, processor_job_lookup_time, pheromone_map, routers, processor_category_profiles, failure_schedule, tcp_connections, cca):
    global global_processor_id  # Reference the global processor ID counter
    processors = []

    for category in range(num_categories):
        for index in range(processors_per_category):
            profile = processor_category_profiles[category]

            # Find the failure schedule for this processor
            if global_processor_id in failure_schedule:
                failure_times = failure_schedule[global_processor_id]['failure_times']
                failure_durations = failure_schedule[global_processor_id]['failure_durations']
                sorted_failures = sorted(zip(failure_times, failure_durations), key=lambda x: x[0])
                failure_times, failure_durations = zip(*sorted_failures)
            else:
                failure_times = []
                failure_durations = []

            processor = Processor(env, global_processor_id, category, resource_pool, routers[category], dtn, profile['compute_speed'], profile['nic_speed'], processor_job_lookup_time, pheromone_map, profile['max_concurrent_jobs'], tcp_connections, cca, failure_times, failure_durations)
            processors.append(processor)
            routers[category].add_route(processor)  # Connect processor to its router
            print(f"Router {routers[category].router_id} connected to Processor {processor.processor_id}")

            # Add the processor to the pheromone map
            if category not in pheromone_map:
                pheromone_map[category] = {}
            pheromone_map[category][global_processor_id] = 0  # Initialize with default load value
            
            print(f"Processor {processor.processor_id} (Category {category}) connected to Router {routers[category].router_id}")
            global_processor_id += 1
    return processors

               
def connect_dtns_and_edge_routers(dtns, edge_routers):
    """
    Connect each DTN to the edge routers, then establish routing between edge routers.
    """
    # Connect DTNs to their respective edge routers
    for dtn, edge_router in zip(dtns, edge_routers):
        edge_router.add_route(dtn)  # Route to the DTN via the edge router
        # dtn.routers[edge_router] = edge_router.nic_speed  # Add edge router to DTN's routing table
        print(f"Edge Router {edge_router.router_id} DTN connected to {dtn.dtn_id}")

    # Establish inter-router routes for edge routers
    for router in edge_routers:
        for other_router in edge_routers:
            if router != other_router:
                router.add_route(other_router)  # Create mesh between edge routers

    # Route DTNs across edge routers
    for router in edge_routers:
        for dtn in dtns:
            # Route via DTN's edge router if not directly connected to this router
            if dtn.edge_router != router:
                router.add_route(dtn, via=dtn.edge_router)  # Route via the DTN's edge router

    print("Mesh network established between edge routers.")



def verify_connections(routers):
    for router in routers:
        print(f"Router {router.router_id} is connected to: {list(router.routing_table.keys())}")
