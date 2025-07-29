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


def create_dumbell_topology(env, args, processor_category_profiles, failure_schedule):
    """Create dumbell topology with 4 sites and bottleneck routers."""
    print("Creating dumbell topology...")
    
    # Override num_sites for dumbell topology
    num_sites = 4
    num_categories = 1  # Single category per site for dumbell
    
    # Create containers
    dtns = []
    edge_routers = []
    bottleneck_routers = []
    dtns_per_site = {}
    routers_per_site = {}
    processors_per_site = {}
    resource_pools_per_site = {}
    tcp_connections_per_site = {}
    
    # Create bottleneck routers (router 0 and router 1)
    from entities.router_fifo import RouterFifo
    from entities.router_fq import RouterFq
    
    for i in range(2):
        if args.aqm == 'fifo':
            bottleneck_router = RouterFifo(env, f"bottleneck_{i}", args.bottleneck_nic_speed, 
                                         args.link_delay, args.bottleneck_queue_size)
        else:
            bottleneck_router = RouterFq(env, f"bottleneck_{i}", args.bottleneck_nic_speed, 
                                       args.link_delay, args.bottleneck_queue_size)
        bottleneck_routers.append(bottleneck_router)
        print(f"Created bottleneck router {i} with {args.bottleneck_nic_speed} Mbps")
    
    # Create 4 sites
    for site_id in range(num_sites):
        print(f"Creating dumbell site {site_id}")
        
        # Each site has single category with specific setup
        category = site_id  # Site 0->cat 0, Site 1->cat 1, Site 2->cat 2, Site 3->cat 3
        site_categories = 1  # Only one category per site
        
        resource_pool = ResourcePool(env, site_categories)
        resource_pools_per_site[site_id] = resource_pool
        
        pheromone_map = create_pheromone_map(site_categories, args.processors_per_category)
        
        # Create routers for the site with edge router
        routers = create_network(env, site_categories, args.router_nic_speed, args.link_delay, 
                               args.router_queue_size, args.aqm, add_edge_router=True)
        routers_per_site[site_id] = routers
        
        tcp_connections = []
        
        # Configure edge router
        edge_router = routers[-1]
        edge_router.nic_speed = args.edge_router_nic_speed
        edge_router.queue_limit = args.edge_router_queue_size
        edge_router.delay = args.edge_router_delay
        edge_routers.append(edge_router)
        
        # Connect edge routers to bottleneck routers
        if site_id in [0, 1]:  # Client sites connect to bottleneck router 0
            bottleneck_router = bottleneck_routers[0]
        else:  # Server sites (2, 3) connect to bottleneck router 1
            bottleneck_router = bottleneck_routers[1]
            
        # Set up routing between edge router and bottleneck router using proper add_route method
        edge_router.add_route(bottleneck_router)
        bottleneck_router.add_route(edge_router)
        
        print(f"Connected site {site_id} edge router to bottleneck router {0 if site_id < 2 else 1}")
        
        # Create DTN
        dtn = DTN(env, routers, args.dtn_nic_speed, tcp_connections, args.cca, args.dtn_data_request)
        dtns.append(dtn)
        dtns_per_site[site_id] = dtn
        
        # Create processors - for server sites (2,3), create minimal processors
        if site_id in [2, 3]:  # Server sites - only one processor per site
            processors_per_category = 1
        else:  # Client sites - normal processor count
            processors_per_category = args.processors_per_category
            
        processors = connect_processors_to_routers(env, site_categories, processors_per_category, 
                                                 resource_pool, dtn, args.processor_job_lookup_time, 
                                                 pheromone_map, routers[:-1], processor_category_profiles, 
                                                 failure_schedule, tcp_connections, args.cca)
        processors_per_site[site_id] = processors
        
        # Connect routers and processors
        connect_routers_and_processors(routers[:-1], processors)
        verify_connections(routers[:-1])
        
        # Add routes from edge router to local processors and DTN for bidirectional communication
        edge_router = routers[-1]  # Last router is edge router
        for processor in processors:
            edge_router.add_route(processor)
            print(f"Added route from edge router {edge_router.router_id} to local processor {processor.processor_id}")
        
        # Add route to local DTN for ACK return traffic
        edge_router.add_route(dtn)
        print(f"Added route from edge router {edge_router.router_id} to local DTN {dtn.dtn_id}")
        
        # Add routes from edge router to local processors via processor's router (for intra-site delivery)
        for processor in processors:
            edge_router.add_route(processor, via=processor.router)
            print(f"Added route from edge router {edge_router.router_id} to local processor {processor.processor_id} via processor router {processor.router.router_id}")
        
        tcp_connections_per_site[site_id] = tcp_connections
    
    # Connect bottleneck routers to each other using proper add_route method
    bottleneck_routers[0].add_route(bottleneck_routers[1])
    bottleneck_routers[1].add_route(bottleneck_routers[0])
    print(f"Connected bottleneck routers 0 and 1 to each other")
    
    # Set up cross-site routing through bottlenecks
    print("Setting up dumbell cross-site routing...")
    for site_id in range(num_sites):
        edge_router = edge_routers[site_id]
        processors_at_this_site = processors_per_site[site_id]
        print(f"Site {site_id} has {len(processors_at_this_site)} processors")
        
        for other_site_id in range(num_sites):
            if site_id != other_site_id:
                target_edge_router = edge_routers[other_site_id]
                target_dtn = dtns_per_site[other_site_id]
                
                # Route through appropriate bottleneck
                if site_id < 2:  # From client sites
                    next_hop = bottleneck_routers[0]
                else:  # From server sites
                    next_hop = bottleneck_routers[1]
                    
                edge_router.add_route(target_edge_router, via=next_hop)
                
                # Route to remote DTNs through bottlenecks
                edge_router.add_route(target_dtn, via=next_hop)
                print(f"Added route from edge router {edge_router.router_id} to DTN site {other_site_id} via bottleneck {next_hop.router_id}")
    
    # Set up bottleneck router routing to reach DTNs at remote sites
    print("Setting up bottleneck router routing...")
    for bottleneck_id, bottleneck_router in enumerate(bottleneck_routers):
        for site_id in range(num_sites):
            edge_router = edge_routers[site_id]
            dtn = dtns_per_site[site_id]
            
            # Bottleneck 0 routes to sites 2,3 DTNs via bottleneck 1
            # Bottleneck 1 routes to sites 0,1 DTNs via bottleneck 0
            if bottleneck_id == 0 and site_id >= 2:  # Bottleneck 0 -> sites 2,3
                bottleneck_router.add_route(dtn, via=bottleneck_routers[1])
                print(f"Added route from bottleneck {bottleneck_router.router_id} to DTN site {site_id} via bottleneck 1")
            elif bottleneck_id == 1 and site_id < 2:  # Bottleneck 1 -> sites 0,1
                bottleneck_router.add_route(dtn, via=bottleneck_routers[0])
                print(f"Added route from bottleneck {bottleneck_router.router_id} to DTN site {site_id} via bottleneck 0")
            elif (bottleneck_id == 0 and site_id < 2) or (bottleneck_id == 1 and site_id >= 2):
                # Direct routes to local sites
                bottleneck_router.add_route(dtn, via=edge_router)
                print(f"Added route from bottleneck {bottleneck_router.router_id} to local DTN site {site_id} via edge router {edge_router.router_id}")
                
                # Also add routes to local processors for DTN-to-processor delivery
                processors = processors_per_site[site_id]
                for processor in processors:
                    bottleneck_router.add_route(processor, via=edge_router)
                    print(f"Added route from bottleneck {bottleneck_router.router_id} to local processor {processor.processor_id} via edge router {edge_router.router_id}")
    
    # Debug: Print routing table summary for bottleneck routers
    for i, bottleneck_router in enumerate(bottleneck_routers):
        print(f"Bottleneck router {i} has {len(bottleneck_router.routing_table)} routing entries")
        for dest, (next_hop, speed) in bottleneck_router.routing_table.items():
            dest_name = getattr(dest, 'router_id', getattr(dest, 'processor_id', f'object_{id(dest)}'))
            next_hop_name = getattr(next_hop, 'router_id', getattr(next_hop, 'processor_id', f'object_{id(next_hop)}'))
            print(f"  Route to {dest_name} (obj {id(dest)}) via {next_hop_name}")
            
    # Debug: Print processor objects in each site for comparison
    for site_id, processors in processors_per_site.items():
        print(f"Site {site_id} processors:")
        for processor in processors:
            print(f"  Processor {processor.processor_id} (obj {id(processor)})")
    
    # Generate jobs simultaneously for dumbell topology to ensure fair TCP competition
    job_category_profiles = _default_job_category_profiles()
    # Use new simultaneous job generation that directly assigns jobs to processors
    # This ensures both TCP connections start at exactly the same time
    env.process(generate_simultaneous_jobs_dumbell(env, processors_per_site, resource_pools_per_site, job_category_profiles, start_time=1.0))
    
    print("Dumbell topology created successfully")
    
    return (dtns, edge_routers, dtns_per_site, routers_per_site, processors_per_site, 
            resource_pools_per_site, tcp_connections_per_site, bottleneck_routers)



def generate_simultaneous_jobs_dumbell(env, processors_per_site, resource_pools_per_site, job_category_profiles, start_time=1.0):
    """Generate and directly assign jobs simultaneously for dumbell topology to ensure perfect TCP competition."""
    yield env.timeout(start_time)
    
    # Create jobs for both client sites simultaneously
    global global_job_id
    job_id_0 = next(global_job_id)
    job_id_1 = next(global_job_id)
    
    # Fixed data volume for testing
    data_volume = 3000  # Large enough for meaningful TCP behavior
    
    # Create jobs directly
    from entities.job import Job
    job_0 = Job(env, job_id_0, 2309, data_volume, 0)  # Site 0 job
    job_1 = Job(env, job_id_1, 1228, data_volume, 0)  # Site 1 job
    
    print(f"Generated simultaneous jobs: Job {job_id_0} for site 0, Job {job_id_1} for site 1 at time {env.now}")
    
    # Get processors from each site (use first processor from each site)
    processor_0 = processors_per_site[0][0]  # First processor at site 0
    processor_1 = processors_per_site[1][0]  # First processor at site 1
    
    # Directly assign jobs to processors and update resource pools
    resource_pools_per_site[0].site_working_pool[0].append(job_0)
    resource_pools_per_site[1].site_working_pool[0].append(job_1)
    
    # Update resource pool ledgers
    ledger_entry_0 = {
        'job_id': job_0.id,
        'site_id': 0,
        'processor_id': processor_0.processor_id,
        'assignment_time': env.now,
        'reassignment_time': None,
        'completion_time': None,
        'waiting_time': 0.0,  # No waiting since directly assigned
        'creation_time': job_0.creation_time
    }
    ledger_entry_1 = {
        'job_id': job_1.id,
        'site_id': 1,
        'processor_id': processor_1.processor_id,
        'assignment_time': env.now,
        'reassignment_time': None,
        'completion_time': None,
        'waiting_time': 0.0,  # No waiting since directly assigned
        'creation_time': job_1.creation_time
    }
    resource_pools_per_site[0].site_ledger[0].append(ledger_entry_0)
    resource_pools_per_site[1].site_ledger[0].append(ledger_entry_1)
    # Also update the global ledger for correct global job counts
    from entities.resourcepool import ResourcePool
    ResourcePool.common_ledger[0].append(ledger_entry_0)
    ResourcePool.common_ledger[0].append(ledger_entry_1)
    
    # Update processor loads
    processor_0.current_job_load += job_0.computation
    processor_1.current_job_load += job_1.computation
    
    print(f"Directly assigned Job {job_0.id} to Processor {processor_0.processor_id} at site 0")
    print(f"Directly assigned Job {job_1.id} to Processor {processor_1.processor_id} at site 1")
    
    # Start both jobs simultaneously using env.process in parallel
    print(f"Starting both jobs simultaneously at time {env.now}")
    env.process(initiate_job_directly(env, processor_0, job_0))
    env.process(initiate_job_directly(env, processor_1, job_1))

def initiate_job_directly(env, processor, job):
    """Directly initiate a job on a processor, bypassing normal resource pool flow."""
    print(f"Processor {processor.processor_id}: Directly initiating job {job.id} at {env.now}")
    
    # Record timing
    job.data_request_time = env.now
    
    # Establish TCP connection and request data immediately
    print(f"Processor {processor.processor_id}: Requesting data for job {job.id} directly")
    connection = processor.establish_connection(job.id)
    
    # Send data request
    yield env.process(connection.send_data(job.data_volume, job.id, 'REQUEST'))
    print(f"Direct data request sent for job {job.id} from Processor {processor.processor_id}")
    
    # Create data event and wait for data
    data_event = env.event()
    processor.waiting_jobs.append((job, data_event))
    
    print(f"Processor {processor.processor_id}: Waiting for data event for job {job.id}")
    yield data_event  # Wait until data arrives
    
    print(f"Processor {processor.processor_id}: Data event triggered for job {job.id}")
    job.data_received_time = env.now
    job.data_arrival_time = job.data_received_time - job.data_request_time
    
    # Process job immediately
    print(f"Processor {processor.processor_id}: Starting immediate processing of job {job.id}")
    yield env.process(processor.process_job(job))
    print(f"Processor {processor.processor_id}: Completed immediate processing of job {job.id}")


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
    parser.add_argument('--topology', choices=['mesh', 'dumbell'], default='mesh', help='Network topology: mesh (current) or dumbell (bottleneck)')
    parser.add_argument('--bottleneck-nic-speed', type=int, default=1000, help='Bottleneck router NIC speed in Mbps for dumbell topology')
    parser.add_argument('--bottleneck-queue-size', type=int, default=25, help='Bottleneck router queue size for dumbell topology')
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
    # Determine number of sites based on topology
    effective_num_sites = 4 if args.topology == 'dumbell' else args.num_sites
    
    # Skip failure generation for dumbell topology (no failures needed)
    if args.topology == 'dumbell':
        failure_schedule = {}  # Empty failure schedule for dumbell
    else:
        number_of_processors = num_categories * args.processors_per_category * effective_num_sites  # Multiply by number of sites
        if args.job_generator == 'replay_with_fault' and args.failure_schedule_file:
            failure_schedule_df = pd.read_csv(args.failure_schedule_file)
        else:
            failure_schedule_df = generate_failure_schedule(number_of_processors, args.random_seed, args.number_of_failures, args.simulation_time, args.max_failure_duration, effective_num_sites)

        # Convert the failure schedule to a dictionary (only for non-dumbell topology)
        failure_schedule = {}
        for _, row in failure_schedule_df.iterrows():
            processor_id = row['processor_id']
            if processor_id not in failure_schedule:
                failure_schedule[processor_id] = {'failure_times': [], 'failure_durations': []}
            failure_schedule[processor_id]['failure_times'].append(row['failure_time'])
            failure_schedule[processor_id]['failure_durations'].append(row['failure_duration'])

    directory = os.path.join(base_directory, str(args.random_seed))


    # Create topology based on user selection
    if args.topology == 'dumbell':
        # Create dumbell topology
        (dtns, edge_routers, dtns_per_site, routers_per_site, processors_per_site, 
         resource_pools_per_site, tcp_connections_per_site, bottleneck_routers) = create_dumbell_topology(
            env, args, processor_category_profiles, failure_schedule)
        
        # Set up dumbell-specific DTN data requests
        # DTN of client site 0 requests data from DTN of server site 2  
        # DTN of client site 1 requests data from DTN of server site 3
        dtns_per_site[0].set_data_source_dtn(dtns_per_site[2])
        dtns_per_site[1].set_data_source_dtn(dtns_per_site[3])
        
        # Set DTN lists for inter-site communication
        for dtn in dtns:
            dtn.set_dtn_list(dtns)
            
    else:
        # Create mesh topology (original implementation)
        # Create containers for DTNs and edge routers if necessary
        dtns = []
        edge_routers = []
        dtns_per_site = {}
        routers_per_site = {}
        processors_per_site = {}
        resource_pools_per_site = {}
        tcp_connections_per_site = {}

        # Create multiple HPC sites in a loop
        for site_id in range(effective_num_sites):
            print(f"Creating HPC site {site_id} out of 0 to {effective_num_sites - 1}")

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

            # --- Mesh Routing Fix: Ensure correct DTN and processor reachability ---
            # 1. Each DTN's edge router has a route to every other DTN (via the appropriate edge router)
            for src_dtn in dtns:
                src_edge_router = src_dtn.edge_router
                for dst_dtn in dtns:
                    if src_dtn != dst_dtn:
                        # Route to remote DTN via its edge router
                        src_edge_router.add_route(dst_dtn, via=dst_dtn.edge_router)

            # 2. Each DTN's edge router has a route to each local processor via the processor's router (for intra-site delivery)
            for site_id, dtn in enumerate(dtns):
                for processor in processors_per_site[site_id]:
                    dtn.edge_router.add_route(processor, via=processor.router)
            # --- End Mesh Routing Fix ---

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
    
    # Collect all TCP connections across all sites for proper inter-site plotting
    all_tcp_connections = []
    for site_connections in tcp_connections_per_site.values():
        all_tcp_connections.extend(site_connections)
    
    for site_id in range(effective_num_sites):
        print(f"Plotting for HPC site {site_id} out of 0 to {effective_num_sites - 1}")
        
        resource_pool = resource_pools_per_site[site_id]
        routers = routers_per_site[site_id]
        processors = processors_per_site[site_id]
        tcp_connections = tcp_connections_per_site[site_id]

        # After running the simulation for each site, generate the plots
        resource_pool_plot_results(resource_pool, directory, args.simulation_time, args.average_interval, site_id)
        processor_visualize_job_data(processors, directory, site_id)
        dtn_plot_data_handling_times(dtn, directory, site_id)
        router_plot_router_load(routers, args.aqm, directory, args.simulation_time, args.average_interval, site_id, args.add_edge_router)
        
        # Use all connections for proper inter-site/intra-site filtering
        plot_tcp_metrics(all_tcp_connections, directory, args.simulation_time, args.average_interval, site_id, args.add_edge_router)
        
        processor_visualize_processor_performance(processors, directory, site_id)
        processor_plot_average_data_arrival_times(processors, directory, args.simulation_time, args.average_interval, site_id)
        processor_visualize_average_performance(processors, directory, site_id)
        dtn_plot_data_handling_time_series(dtn, directory, args.simulation_time, args.average_interval, site_id)
        router_calculate_and_plot_average_wait_times(routers, args.aqm, directory, args.simulation_time, args.average_interval, site_id, args.add_edge_router)

    # Generate combined plots for dumbell topology
    if args.topology == 'dumbell':
        from visualization.plotting import plot_combined_cwnd_dumbell, plot_combined_throughput_dumbell, plot_combined_retransmissions_dumbell, plot_combined_rtt_dumbell
        
        # Calculate maximum completion time across all connections for consistent x-axis
        max_completion_time = 0
        for site_id, connections in tcp_connections_per_site.items():
            for conn in connections:
                # Check if this is an inter-site DTN-to-DTN connection with throughput data
                if (isinstance(conn.src, DTN) and isinstance(conn.dst, DTN) and 
                    hasattr(conn, 'throughput_log') and not conn.throughput_log.empty):
                    
                    times = conn.throughput_log['time'].tolist()
                    if times:
                        max_completion_time = max(max_completion_time, max(times))
        
        # If no completion time found, use simulation time
        if max_completion_time == 0:
            max_completion_time = args.simulation_time
        
        # Add 3 seconds buffer for better visualization
        max_completion_time += 0.5
        
        print(f"\n=== MAXIMUM TRANSMISSION COMPLETION TIME: {max_completion_time:.1f} seconds ===")
        
        # Generate full range plots (using max completion time)
        print("\n=== GENERATING FULL RANGE PLOTS (0 to max completion time) ===")
        plot_combined_cwnd_dumbell(tcp_connections_per_site, directory, max_completion_time)
        plot_combined_throughput_dumbell(tcp_connections_per_site, directory, max_completion_time)
        plot_combined_rtt_dumbell(tcp_connections_per_site, directory, max_completion_time)
        plot_combined_retransmissions_dumbell(tcp_connections_per_site, directory, max_completion_time)
        
        # Generate detailed plots for 0-10 seconds range
        print("\n=== GENERATING DETAILED PLOTS (0 to 10 seconds) ===")
        detailed_time_range = (0, 10)
        plot_combined_cwnd_dumbell(tcp_connections_per_site, directory, max_completion_time, time_range=detailed_time_range)
        plot_combined_throughput_dumbell(tcp_connections_per_site, directory, max_completion_time, time_range=detailed_time_range)
        plot_combined_rtt_dumbell(tcp_connections_per_site, directory, max_completion_time, time_range=detailed_time_range)
        plot_combined_retransmissions_dumbell(tcp_connections_per_site, directory, max_completion_time, time_range=detailed_time_range)

if __name__ == "__main__":
    main()
