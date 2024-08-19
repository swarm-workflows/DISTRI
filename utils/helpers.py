import pandas as pd
import simpy
import random
from entities.task import Task
from entities.processor import Processor
from entities.router_fifo import *
from entities.router_fq import *


def task_generator(env, resource_pool, num_categories, category_profiles, seed=None):
    # Seed the random number generator for reproducibility
    if seed is not None:
        random.seed(seed)

    task_id = 0
    while True:
        category = random.randint(0, num_categories - 1)
        profile = category_profiles[category]

        # Adjusted task property generation based on category profile
        computation = random.randint(profile['mean_comp'], profile['max_comp'])
        data_volume = random.randint(profile['mean_data'], profile['max_data'])

        # Create and add a new task to the resource pool
        task = Task(env, task_id, computation, data_volume, category)
        resource_pool.add_task(task)  # Add the task to the pool
        # print(f"Generated and added task {task.id} in category {task.category} to pool with comp {computation} and vol {data_volume}. Total tasks now: {len(resource_pool.pools[task.category].items)}")
        task_id += 1
        yield env.timeout(random.uniform(1.1, 3.0))  # New tasks are generated every 0.1 - 1.0 time units

def task_replay(env, resource_pool, log_file):
    df = pd.read_csv(log_file)
    for i, row in df.iterrows():
        task = Task(env, i, row.computation, row.data, row.category)
        resource_pool.add_task(task)
        yield env.timeout(random.uniform(0.1, 1.0))

def create_pheromone_map(num_categories, processors_per_category):
    pheromone_map = {category: {} for category in range(num_categories)}
    for category in range(num_categories):
        min_in_category = category * processors_per_category
        max_in_category = (category + 1) * processors_per_category
        for processor_id in range(min_in_category, max_in_category):
            pheromone_map[category][processor_id] = 0  # Initialize pheromone levels using unique processor ID
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


def create_network(env, num_categories, nic_speed, delay, queue_limit, aqm):
    # Create a router for each category with a unique router_id
    if aqm == 'fifo':
        routers = [RouterFifo(env, i, nic_speed, delay, queue_limit) for i in range(num_categories)]
    elif aqm == 'fq':
        routers = [RouterFq(env, i, nic_speed, delay, queue_limit) for i in range(num_categories)]
    else:
        raise ValueError('AQM Error: Unsupported AQM input "{}"'.format(aqm))
    return routers

def connect_processors_to_routers(env, num_categories, processors_per_category, resource_pool, dtn, processor_task_lookup_time, pheromone_map, routers, processor_category_profiles, failure_schedule, tcp_connections, cca):
    processors = []
    processor_id = 0  # Initialize a counter to generate unique processor IDs
    for category in range(num_categories):
        for index in range(processors_per_category):
            profile = processor_category_profiles[category]

            # Find the failure schedule for this processor
            if processor_id in failure_schedule:
                # Extract and sort the failure times and durations based on failure times
                failure_times = failure_schedule[processor_id]['failure_times']
                failure_durations = failure_schedule[processor_id]['failure_durations']
                sorted_failures = sorted(zip(failure_times, failure_durations), key=lambda x: x[0])
                failure_times, failure_durations = zip(*sorted_failures)
            else:
                failure_times = []
                failure_durations = []

            processor = Processor(env, processor_id, category, resource_pool, routers[category], dtn, profile['compute_speed'], profile['nic_speed'], processor_task_lookup_time, pheromone_map, profile['max_concurrent_tasks'], tcp_connections, cca, failure_times, failure_durations)
            processors.append(processor)
            routers[category].add_route(processor)  # Connect processor to its router
            print(f"Processor {processor_id} (Category {category}) connected to Router {routers[category].router_id}")
            processor_id += 1
    return processors

def verify_connections(routers):
    for router in routers:
        print(f"Router {router.router_id} is connected to: {list(router.routing_table.keys())}")
