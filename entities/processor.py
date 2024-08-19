import simpy
from entities.packet import Packet
from collections import defaultdict
from protocols.tcp import TCPConnection, TCPSegment

class Processor:
    def __init__(self, env, processor_id, category, resource_pool, router, dtn, compute_speed, nic_speed, task_lookup, pheromone_map, max_concurrent_tasks, tcp_connections, cca='reno', failure_times=[], failure_durations=[]):
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
        self.failure_times = failure_times
        self.failure_durations = failure_durations
        self.cca = cca
        self.connections = defaultdict(lambda: defaultdict(TCPConnection))  # Dictionary to store connections per task ID and connection ID
        self.received_data = defaultdict(lambda: defaultdict(list))  # Store received data segments for each task and connection
        self.expected_seq = defaultdict(lambda: defaultdict(int))  # Track the expected sequence number for each task and connection
        self.is_failed = False  # Flag to indicate processor failure
        self.tcp_connections = tcp_connections  # Reference to the global list of TCP connections
        self.env.process(self.task_manager())  # Continuously check for new task
        self.env.process(self.process_tasks())  # Continuously run task processing
        if self.failure_times and self.failure_durations:
            self.env.process(self.simulate_failures())

    def establish_connection(self, task_id):
        connection = TCPConnection(self.env, self, self.dtn, self.nic_speed, self.dtn.nic_speed, self.router, self.cca)
        self.connections[task_id][connection.connection_id] = connection
        self.tcp_connections.append(connection)  # Add the new connection to the global list
        return connection

    def simulate_failures(self):
        """Simulates failures based on the provided failure times and durations."""
        for failure_time, failure_duration in zip(self.failure_times, self.failure_durations):
            yield self.env.timeout(failure_time - self.env.now)
            print(f"Processor {self.processor_id} is simulating a failure at time {self.env.now} for {failure_duration} time units.")
            self.is_failed = True  # Indicate that the processor is in a failed state
            # Reset tasks and simulate failure
            self.waiting_tasks = []
            self.ready_tasks = []
            self.is_processing_task = False
            self.current_task_load = 0
            yield self.env.timeout(failure_duration)
            print(f"Processor {self.processor_id} has recovered from failure state at time {self.env.now}.")
            self.is_failed = False  # Indicate that the processor has recovered
            # Reset again to ensure a fresh start
            self.waiting_tasks = []
            self.ready_tasks = []
            self.is_processing_task = False
            self.current_task_load = 0

            self.env.process(self.task_manager())
            self.env.process(self.process_tasks())

    def task_manager(self):
        """ Continuously checks for new tasks and handles them, respecting system limits. """
        while True:
            try:
                if self.is_failed:  # Check if the processor is in a failed state
                    yield self.env.timeout(self.task_lookup)
                    continue

                if self.is_eligible_for_task() and len(self.waiting_tasks) < self.MAX_CONCURRENT_TASKS:
                    # print(f"Processor {self.processor_id}: Checking for tasks.")
                    try:
                        task = yield from self.resource_pool.assign_task(self.category, self.processor_id, self)
                        if task is not None:
                            self.current_task_load += task.computation
                            self.update_pheromone_levels()
                            self.env.process(self.initiate_task(task))
                            print(f"Processor {self.processor_id}: Task {task.id} assigned.")
                    except Exception as e:
                        print(f"Processor {self.processor_id}: Error assigning task - {e}")
                else:
                    self.resource_pool.update_heartbeat(self.processor_id, self.env.now, self)
                    # print(f"Processor {self.processor_id}: Not eligible or max tasks reached.")
                
                yield self.env.timeout(self.task_lookup)  # Wait task_lookup time before checking the resource pool for new task again
            except Exception as e:
                print(f"Processor {self.processor_id}: Exception in task_manager - {e}")
                yield self.env.timeout(self.task_lookup)

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
            try:
                if self.is_failed:  # Check if the processor is in a failed state
                    yield self.env.timeout(self.task_lookup)
                    continue

                if self.ready_tasks and not self.is_processing_task:
                    self.is_processing_task = True
                    task = self.ready_tasks.pop(0)  # Get the first task that's ready
                    print(f"Processor {self.processor_id}: Starting task {task.id}.")
                    yield self.env.process(self.process_task(task))
                    self.is_processing_task = False
                    print(f"Processor {self.processor_id}: Completed task {task.id}.")
                    self.current_task_load -= task.computation
                    self.update_pheromone_levels()
                else:
                    # print(f"Processor {self.processor_id}: No task to process.")
                    yield self.env.timeout(0.5)  # Wait a bit before checking again
            except Exception as e:
                print(f"Processor {self.processor_id}: Exception in process_tasks - {e}")
                yield self.env.timeout(0.5)
    
    def process_task(self, task):
        """ Processes the task. """
        task.start_time = self.env.now
        process_time = task.computation / self.compute_speed
        yield self.env.timeout(process_time)
        task.end_time = self.env.now
        task.total_processing_time = task.end_time - task.start_time
        self.task_records.append(task)
        print(f"Processor {self.category}: Completed processing task {task.id} at {self.env.now}")

        self.resource_pool.complete_task(task, self.category, self)  # Mark the task as completed in the ledger

    def request_data(self, task):
        """ Sends a data request for the task to the DTN through the router. """
        print(f"Processor {self.processor_id} requesting data for task {task.id}")
        connection = self.establish_connection(task.id)  # Ensure the connection is established
        yield self.env.process(connection.send_data(task.data_volume, task.id, 'REQUEST'))
        print(f"Data request sent for task {task.id} to DTN from Processor {self.processor_id} via Router {self.router.router_id}")

    def receive_data_sent_flag(self, task_id):
        """ Handles reception of the data sent flag from the DTN. """
        for task, event in self.waiting_tasks:
            if task.id == task_id:
                event.succeed()
                self.waiting_tasks.remove((task, event))
                break

    def data_waiting_task(self, task_id):
        """ Handles reception of the data sent flag from the DTN. """
        for task, event in self.waiting_tasks:
            if task.id == task_id:
                return True   
            else:
                return False
            
    def receive_packet(self, packet):
        """Handles packet reception."""
        if packet.packet_type == 'tcp_segment':
            print(f"Processor {self.processor_id} received packet for task {packet.task_id} with connection id {packet.connection_id} at {self.env.now}")
            self.connections[packet.task_id][packet.connection_id] = packet.connection
            segment = TCPSegment(seq=packet.segment_seq, ack=packet.segment_ack, flags=packet.segment_flag, task_id=packet.task_id, connection_id=packet.connection_id, data=packet.data, data_volume=packet.data_volume, missing_segments=packet.missing_segments)
            yield self.env.process(self.connections[packet.task_id][packet.connection_id].receive_segment(segment))

    def is_eligible_for_task(self):
        """Determines if this processor should take a new task based on pheromone levels."""
        # A processor takes a task if its pheromone level is in the lowest 30%
        try:
            all_levels = list(self.pheromone_map[self.category].values())
            threshold = sorted(all_levels)[int(len(all_levels) * 0.3)]  # Find the 30th percentile level
            eligible = self.pheromone_map[self.category][self.processor_id] <= threshold
            # print(f"Processor {self.processor_id} eligibility check: {eligible} with load {self.pheromone_map[self.category][self.processor_id]} and threshold {threshold}")
            return eligible
        except Exception as e:
            print(f"Exception in eligibility check for processor {self.processor_id}: {e}")
            return False

    def stop_task(self, task_id):
        """Stops the task with the given task_id."""
        # Remove task from waiting or ready tasks if it exists
        self.waiting_tasks = [(task, event) for task, event in self.waiting_tasks if task.id != task_id]
        self.ready_tasks = [task for task in self.ready_tasks if task.id != task_id]
        print(f"Processor {self.processor_id}: Task {task_id} stopped.")

    def receive_segment(self, segment):
        print(f"Processor received segment {segment.flags} for task {segment.task_id} with connection id {segment.connection_id} at {self.env.now}")

        if segment.flags == 'FIN':
            print(f"Processor completed receiving data request for task {segment.task_id}")
            self.receive_data_sent_flag(segment.task_id)
            if segment.task_id in self.connections and segment.connection_id in self.connections[segment.task_id]:
                connection = self.connections[segment.task_id][segment.connection_id]
                if connection.state != 'CLOSED':
                    connection.close()
            del self.connections[segment.task_id][segment.connection_id]
            return None

        else:        
            # Initialize the received data structure if not already done
            if segment.task_id not in self.received_data:
                self.received_data[segment.task_id] = defaultdict(list)
                print(f"Initialized received_data for task {segment.task_id}")

            if segment.connection_id not in self.received_data[segment.task_id]:
                self.received_data[segment.task_id][segment.connection_id] = []
                print(f"Initialized received_data for connection {segment.connection_id} in task {segment.task_id}")

            # Check for duplicates before appending
            if segment.seq not in [seg.seq for seg in self.received_data[segment.task_id][segment.connection_id]]:
                self.received_data[segment.task_id][segment.connection_id].append(segment)

            # Print received data before sorting
            # print(f"Received data before sorting: {[seg.seq for seg in self.received_data[segment.task_id][segment.connection_id]]}")


            # Ensure segments are stored in ascending order of sequence numbers
            self.received_data[segment.task_id][segment.connection_id].sort(key=lambda x: x.seq)

            # Print received data after sorting
            # print(f"Received data after sorting: {[seg.seq for seg in self.received_data[segment.task_id][segment.connection_id]]}")

            # Find missing segments
            missing_segments = []
            ack_number = None
            expected_seq = 0  # Start with 0 as the initial expected sequence number

            for seg in self.received_data[segment.task_id][segment.connection_id]:
                if seg.seq == expected_seq:
                    expected_seq += 1
                else:
                    # Find missing segments between expected_seq and seg.seq
                    for missing_seq in range(expected_seq, seg.seq):
                        if ack_number is None:
                            ack_number = missing_seq + 1
                        missing_segments.append(missing_seq)
                    expected_seq = seg.seq + 1

            if ack_number is None:
                ack_number = expected_seq

            # print(f"Missing segments: {missing_segments}")
            print(f"ACK number: {ack_number}")

            return {
                "missing_segments": missing_segments,
                "ack_number": ack_number
            }
            # # Find the maximum in-order sequence number
            # latest_in_order_seq = -1  # Start with -1 to increment to 0 with the first segment

            # for seg in self.received_data[segment.task_id][segment.connection_id]:
            #     if seg.seq == latest_in_order_seq + 1:
            #         latest_in_order_seq = seg.seq
            #     else:
            #         break

            # # Increment the latest in-order sequence to represent the next expected sequence number
            # latest_in_order_seq += 1
            

            # print(f"Updated latest_in_order_seq: {latest_in_order_seq-1} for task {segment.task_id} and connection {segment.connection_id}")

            # return latest_in_order_seq

