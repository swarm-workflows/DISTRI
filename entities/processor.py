import simpy
from entities.packet import Packet

class Processor:
    def __init__(self, env, processor_id, category, resource_pool, router, dtn, compute_speed, nic_speed, task_lookup, pheromone_map, max_concurrent_tasks):
        self.env = env
        self.processor_id = processor_id
        self.category = category
        self.router = router
        self.dtn = dtn
        self.resource_pool = resource_pool
        self.compute_speed = compute_speed
        self.nic_speed = nic_speed
        self.task_lookup = task_lookup  # interval for visiting resource pool to look for new task
        self.pheromone_map = pheromone_map
        self.waiting_tasks = []  # Tasks waiting for data
        self.ready_tasks = []  # Tasks ready to be processed
        self.is_processing_task = False  # Flag to check if a task is currently being processed
        self.current_task_load = 0  # Current total computation time of tasks
        self.task_records = []  # Store comprehensive task records
        self.MAX_CONCURRENT_TASKS = max_concurrent_tasks  # Maximum number of concurrent tasks
        self.env.process(self.task_manager())  # Continuously check for new task
        self.env.process(self.process_tasks())  # Continuously run task processing


    def task_manager(self):
        """ Continuously checks for new tasks and handles them, respecting system limits. """
        while True:
            # Debugging: Check if processor is eligible for a new task
            if self.is_eligible_for_task() and len(self.waiting_tasks) < self.MAX_CONCURRENT_TASKS:
                print(f"Processor {self.processor_id}: Checking for tasks.")
                try:
                    task = yield from self.resource_pool.assign_task(self.category, self.processor_id)
                    self.current_task_load += task.computation
                    self.update_pheromone_levels()
                    self.env.process(self.initiate_task(task))
                    print(f"Processor {self.processor_id}: Task {task.id} assigned.")
                except Exception as e:
                    print(f"Processor {self.processor_id}: Error assigning task - {e}")
            else:
                print(f"Processor {self.processor_id}: Not eligible or max tasks reached.")
            
            yield self.env.timeout(self.task_lookup)  # Wait task_lookup time before checking the resource pool for new task again

    def update_pheromone_levels(self):
        """Updates the pheromone map with the current load."""
        self.pheromone_map[self.category][self.processor_id] = self.current_task_load

    def initiate_task(self, task):
        """ Handles the initial stages of the task. """
        print(f"Processor {self.processor_id}: Initiating task {task.id}.")
        task.data_request_time = self.env.now  # Record the time when data is requested
        print(f"Processor {self.processor_id}: Requesting data for {task.id} from initiate_task.")
        yield self.env.process(self.request_data(task))
        data_event = self.env.event()
        self.waiting_tasks.append((task, data_event))
        yield data_event  # Wait here until the data arrives
        task.data_received_time = self.env.now  # Record the time when data is received
        task.data_arrival_time = task.data_received_time - task.data_request_time
        self.ready_tasks.append(task)  # Move task to ready queue when data is received
        print(f"Data for task {task.id} received by processor {self.processor_id}")

    def process_tasks(self):
        """ Processes tasks sequentially as they become ready. """
        while True:
            if self.ready_tasks and not self.is_processing_task:
                self.is_processing_task = True
                task = self.ready_tasks.pop(0)  # Get the first task that's ready
                print(f"Processor {self.processor_id}: Starting task {task.id}.")
                yield self.env.process(self.process_task(task))
                self.is_processing_task = False
                print(f"Processor {self.processor_id}: Completed task {task.id}.")
                self.current_task_load -= task.computation
                self.update_pheromone_levels()
                # yield self.env.timeout(1)  # Wait a bit before checking again
            else:
                print(f"Processor {self.processor_id}: No task to process.")
                yield self.env.timeout(0.5)  # Wait a bit before checking again
    
    def process_task(self, task):
        """ Processes the task. """
        task.start_time = self.env.now
        process_time = task.computation / self.compute_speed
        yield self.env.timeout(process_time)
        task.end_time = self.env.now
        task.total_processing_time = task.end_time - task.start_time
        self.task_records.append(task)
        print(f"Processor {self.category}: Completed processing task {task.id} at {self.env.now}")

        self.resource_pool.complete_task(task, self.category)  # Mark the task as completed in the ledger

    def request_data(self, task):
        """ Sends a data request for the task to the DTN through the router. """
        print(f"Processor {self.processor_id} requesting data for task {task.id}")
        data_request_packet = Packet(
            source=self,
            destination=self.dtn,
            packet_type='data_request',
            task_id=task.id,
            data_volume=task.data_volume
        )
        # Simulate data transmission delay based on the minimum NIC speed between the processor and the router
        transfer_speed = min(self.nic_speed, self.router.nic_speed)
        yield self.env.timeout(task.data_volume / transfer_speed)
        # Send the data request packet to the router
        self.router.receive_packet(data_request_packet)
        print(f"Data request sent for task {task.id} to DTN from Processor {self.processor_id} via Router {self.router.router_id}")


    def receive_data_sent_flag(self, task_id):
        """ Handles reception of the data sent flag from the DTN. """
        for task, event in self.waiting_tasks:
            if task.id == task_id:
                event.succeed()
                self.waiting_tasks.remove((task, event))
                break

    def receive_packet(self, packet):
        """Handles packet reception."""
        print(f"Processor {self.processor_id} received packet for task {packet.task_id}")
        if packet.packet_type == 'data_complete':
            self.receive_data_sent_flag(packet.task_id)

    def is_eligible_for_task(self):
        """Determines if this processor should take a new task based on pheromone levels."""
        # A processor takes a task if its pheromone level is in the lowest 30%
        try:
            all_levels = list(self.pheromone_map[self.category].values())
            threshold = sorted(all_levels)[int(len(all_levels) * 0.3)]  # Find the 30th percentile level
            eligible = self.pheromone_map[self.category][self.processor_id] <= threshold
            print(f"Processor {self.processor_id} eligibility check: {eligible} with load {self.pheromone_map[self.category][self.processor_id]} and threshold {threshold}")
            return eligible
        except Exception as e:
            print(f"Exception in eligibility check for processor {self.processor_id}: {e}")
            return False