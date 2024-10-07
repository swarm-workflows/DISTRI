import simpy
from entities.packet import Packet
from collections import defaultdict
from protocols.tcp import TCPConnection, TCPSegment

class Processor:
    def __init__(self, env, processor_id, category, resource_pool, router, dtn, compute_speed, nic_speed, job_lookup, pheromone_map, max_concurrent_jobs, tcp_connections, cca='reno', failure_times=[], failure_durations=[]):
        self.env = env
        self.processor_id = processor_id
        self.category = category
        self.router = router
        self.dtn = dtn
        self.resource_pool = resource_pool
        self.compute_speed = compute_speed
        self.nic_speed = nic_speed
        self.job_lookup = job_lookup  # interval for visiting resource pool to look for new job
        self.pheromone_map = pheromone_map
        self.waiting_jobs = []  # Jobs waiting for data
        self.ready_jobs = []  # Jobs ready to be processed
        self.is_processing_job = False  # Flag to check if a job is currently being processed
        self.current_job_load = 0  # Current total computation time of jobs
        self.job_records = []  # Store comprehensive job records
        self.MAX_CONCURRENT_JOBS = max_concurrent_jobs  # Maximum number of concurrent jobs
        self.failure_times = failure_times
        self.failure_durations = failure_durations
        self.cca = cca
        self.connections = defaultdict(lambda: defaultdict(TCPConnection))  # Dictionary to store connections per job ID and connection ID
        self.received_data = defaultdict(lambda: defaultdict(list))  # Store received data segments for each job and connection
        self.expected_seq = defaultdict(lambda: defaultdict(int))  # Track the expected sequence number for each job and connection
        self.is_failed = False  # Flag to indicate processor failure
        self.tcp_connections = tcp_connections  # Reference to the global list of TCP connections
        self.env.process(self.job_manager())  # Continuously check for new job
        self.env.process(self.process_jobs())  # Continuously run job processing
        if self.failure_times and self.failure_durations:
            self.env.process(self.simulate_failures())

    def establish_connection(self, job_id):
        connection = TCPConnection(self.env, self, self.dtn, self.nic_speed, self.dtn.nic_speed, self.router, self.cca)
        self.connections[job_id][connection.connection_id] = connection
        self.tcp_connections.append(connection)  # Add the new connection to the global list
        print(f"Processor {self.processor_id}: initiated TCP connection for job {job_id} with DTN {self.dtn.dtn_id} via Router {self.router.router_id} at time {self.env.now}.")
        return connection


    def simulate_failures(self):
        """Simulates failures based on the provided failure times and durations."""
        for failure_time, failure_duration in zip(self.failure_times, self.failure_durations):
            time_to_failure = failure_time - self.env.now

            # Ensure that time_to_failure is not negative
            if time_to_failure > 0:
                yield self.env.timeout(time_to_failure)
                print(f"Processor {self.processor_id} is simulating a failure at time {self.env.now} for {failure_duration} time units.")
                self.is_failed = True  # Indicate that the processor is in a failed state

                # Reset jobs and simulate failure
                self.waiting_jobs = []
                self.ready_jobs = []
                self.is_processing_job = False
                self.current_job_load = 0

                yield self.env.timeout(failure_duration)
                print(f"Processor {self.processor_id} has recovered from failure state at time {self.env.now}.")
                self.is_failed = False  # Indicate that the processor has recovered

                # Reset again to ensure a fresh start
                self.waiting_jobs = []
                self.ready_jobs = []
                self.is_processing_job = False
                self.current_job_load = 0

                # Restart job management after recovery
                self.env.process(self.job_manager())
                self.env.process(self.process_jobs())
            else:
                print(f"Skipping failure for Processor {self.processor_id} as failure time {failure_time} has already passed at {self.env.now}.")


    def job_manager(self):
        """ Continuously checks for new jobs and handles them, respecting system limits. """
        while True:
            try:
                if self.is_failed:  # Check if the processor is in a failed state
                    yield self.env.timeout(self.job_lookup)
                    continue

                if self.is_eligible_for_job() and len(self.waiting_jobs) < self.MAX_CONCURRENT_JOBS:
                    # print(f"Processor {self.processor_id}: Checking for jobs.")
                    try:
                        job = yield from self.resource_pool.assign_job(self.category, self.processor_id, self)
                        if job is not None:
                            self.current_job_load += job.computation
                            self.update_pheromone_levels()
                            self.env.process(self.initiate_job(job))
                            print(f"Processor {self.processor_id}: Job {job.id} assigned.")
                    except Exception as e:
                        print(f"Processor {self.processor_id}: Error assigning job - {e}")
                else:
                    self.resource_pool.update_heartbeat(self.processor_id, self.env.now, self)
                    # print(f"Processor {self.processor_id}: Not eligible or max jobs reached.")
                
                yield self.env.timeout(self.job_lookup)  # Wait job_lookup time before checking the resource pool for new job again
            except Exception as e:
                print(f"Processor {self.processor_id}: Exception in job_manager - {e}")
                yield self.env.timeout(self.job_lookup)

    def update_pheromone_levels(self):
        """Updates the pheromone map with the current load."""
        self.pheromone_map[self.category][self.processor_id] = self.current_job_load

    def initiate_job(self, job):
        """ Handles the initial stages of the job. """
        print(f"Processor {self.processor_id}: Initiating job {job.id}.")
        job.data_request_time = self.env.now  # Record the time when data is requested
        print(f"Processor {self.processor_id}: Requesting data for {job.id} from initiate_job.")
        yield self.env.process(self.request_data(job))
        data_event = self.env.event()
        self.waiting_jobs.append((job, data_event))
        yield data_event  # Wait here until the data arrives
        job.data_received_time = self.env.now  # Record the time when data is received
        job.data_arrival_time = job.data_received_time - job.data_request_time
        self.ready_jobs.append(job)  # Move job to ready queue when data is received
        print(f"Data for job {job.id} received by processor {self.processor_id}")

    def process_jobs(self):
        """ Processes jobs sequentially as they become ready. """
        while True:
            try:
                if self.is_failed:  # Check if the processor is in a failed state
                    yield self.env.timeout(self.job_lookup)
                    continue

                if self.ready_jobs and not self.is_processing_job:
                    self.is_processing_job = True
                    job = self.ready_jobs.pop(0)  # Get the first job that's ready
                    print(f"Processor {self.processor_id}: Starting job {job.id}.")
                    yield self.env.process(self.process_job(job))
                    self.is_processing_job = False
                    print(f"Processor {self.processor_id}: Completed job {job.id}.")
                    self.current_job_load -= job.computation
                    self.update_pheromone_levels()
                else:
                    # print(f"Processor {self.processor_id}: No job to process.")
                    yield self.env.timeout(0.5)  # Wait a bit before checking again
            except Exception as e:
                print(f"Processor {self.processor_id}: Exception in process_jobs - {e}")
                yield self.env.timeout(0.5)
    
    def process_job(self, job):
        """ Processes the job. """
        job.start_time = self.env.now
        process_time = job.computation / self.compute_speed
        yield self.env.timeout(process_time)
        job.end_time = self.env.now
        job.total_processing_time = job.end_time - job.start_time
        self.job_records.append(job)
        print(f"Processor {self.category}: Completed processing job {job.id} at {self.env.now}")

        self.resource_pool.complete_job(job, self.category, self)  # Mark the job as completed in the ledger

    def request_data(self, job):
        """ Sends a data request for the job to the DTN through the router. """
        print(f"Processor {self.processor_id} requesting data for job {job.id}")
        connection = self.establish_connection(job.id)  # Ensure the connection is established
        yield self.env.process(connection.send_data(job.data_volume, job.id, 'REQUEST'))
        print(f"Data request sent for job {job.id} to DTN from Processor {self.processor_id} via Router {self.router.router_id}")

    def receive_data_sent_flag(self, job_id):
        """ Handles reception of the data sent flag from the DTN. """
        for job, event in self.waiting_jobs:
            if job.id == job_id:
                event.succeed()
                self.waiting_jobs.remove((job, event))
                break

    def data_waiting_job(self, job_id):
        """ Handles reception of the data sent flag from the DTN. """
        for job, event in self.waiting_jobs:
            if job.id == job_id:
                return True   
            else:
                return False
            
    def receive_packet(self, packet):
        """Handles packet reception."""
        if packet.packet_type == 'tcp_segment':
            print(f"Processor {self.processor_id} received packet for job {packet.job_id} with connection id {packet.connection_id} at {self.env.now}")
            self.connections[packet.job_id][packet.connection_id] = packet.connection
            segment = TCPSegment(seq=packet.segment_seq, ack=packet.segment_ack, flags=packet.segment_flag, job_id=packet.job_id, connection_id=packet.connection_id, data=packet.data, data_volume=packet.data_volume, missing_segments=packet.missing_segments)
            yield self.env.process(self.connections[packet.job_id][packet.connection_id].receive_segment(segment))
        else:
            print(f"Receiving packet {packet}")
            # Ensure there is some yield or process simulation inside
            yield self.env.timeout(0)  # Simulate packet processing

    # def is_eligible_for_job(self):
    #     """Determines if this processor should take a new job based on pheromone levels."""
    #     # A processor takes a job if its pheromone level is in the lowest 30%
    #     try:
    #         all_levels = list(self.pheromone_map[self.category].values())
    #         threshold = sorted(all_levels)[int(len(all_levels) * 0.3)]  # Find the 30th percentile level
    #         eligible = self.pheromone_map[self.category][self.processor_id] <= threshold
    #         print(f"Processor {self.processor_id} eligibility check: {eligible} with load {self.pheromone_map[self.category][self.processor_id]} and threshold {threshold}")
    #         return eligible
    #     except Exception as e:
    #         print(f"Exception in eligibility check for processor {self.processor_id}: {e}")
    #         return False

    def is_eligible_for_job(self):
        """Determines if this processor should take a new job based on pheromone levels."""
        # A processor takes a job if its pheromone level is in the lowest 30%
        try:
            # Ensure processor category exists in the pheromone map
            if self.category not in self.pheromone_map:
                raise KeyError(f"Category {self.category} not found in pheromone_map")

            # Ensure processor ID exists within the category
            if self.processor_id not in self.pheromone_map[self.category]:
                raise KeyError(f"Processor {self.processor_id} not found in pheromone_map category {self.category}")

            # Calculate threshold and eligibility
            all_levels = list(self.pheromone_map[self.category].values())
            if not all_levels:
                raise ValueError("Pheromone levels are empty")
                
            threshold = sorted(all_levels)[int(len(all_levels) * 0.3)]
            eligible = self.pheromone_map[self.category][self.processor_id] <= threshold
            print(f"Processor {self.processor_id} eligibility check: {eligible} with load {self.pheromone_map[self.category][self.processor_id]} and threshold {threshold}")
            return eligible
        except Exception as e:
            print(f"Exception in eligibility check for processor {self.processor_id}: {e}")
            return False



    def stop_job(self, job_id):
        """Stops the job with the given job_id."""
        # Remove job from waiting or ready jobs if it exists
        self.waiting_jobs = [(job, event) for job, event in self.waiting_jobs if job.id != job_id]
        self.ready_jobs = [job for job in self.ready_jobs if job.id != job_id]
        print(f"Processor {self.processor_id}: Job {job_id} stopped.")

    def receive_segment(self, segment):
        print(f"Processor {self.processor_id}: received segment {segment.flags} for job {segment.job_id} with connection id {segment.connection_id} at {self.env.now}")

        if segment.flags == 'FIN':
            print(f"Processor {self.processor_id}: completed receiving data request for job {segment.job_id}")
            self.receive_data_sent_flag(segment.job_id)
            if segment.job_id in self.connections and segment.connection_id in self.connections[segment.job_id]:
                connection = self.connections[segment.job_id][segment.connection_id]
                if connection.state != 'CLOSED':
                    connection.close()
            del self.connections[segment.job_id][segment.connection_id]
            return None

        else:        
            # Initialize the received data structure if not already done
            if segment.job_id not in self.received_data:
                self.received_data[segment.job_id] = defaultdict(list)
                print(f"Initialized received_data for job {segment.job_id}")

            if segment.connection_id not in self.received_data[segment.job_id]:
                self.received_data[segment.job_id][segment.connection_id] = []
                print(f"Initialized received_data for connection {segment.connection_id} in job {segment.job_id}")

            # Check for duplicates before appending
            if segment.seq not in [seg.seq for seg in self.received_data[segment.job_id][segment.connection_id]]:
                self.received_data[segment.job_id][segment.connection_id].append(segment)

            # Print received data before sorting
            # print(f"Received data before sorting: {[seg.seq for seg in self.received_data[segment.job_id][segment.connection_id]]}")


            # Ensure segments are stored in ascending order of sequence numbers
            self.received_data[segment.job_id][segment.connection_id].sort(key=lambda x: x.seq)

            # Print received data after sorting
            # print(f"Received data after sorting: {[seg.seq for seg in self.received_data[segment.job_id][segment.connection_id]]}")

            # Find missing segments
            missing_segments = []
            ack_number = None
            expected_seq = self.expected_seq[segment.job_id][segment.connection_id]  # Start with 0 as the initial expected sequence number

            for seg in self.received_data[segment.job_id][segment.connection_id]:
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

            # Update the expected sequence for future segments
            self.expected_seq[segment.job_id][segment.connection_id] = expected_seq
            
            # print(f"Missing segments: {missing_segments}")
            print(f"ACK number: {ack_number}")

            return {
                "missing_segments": missing_segments,
                "ack_number": ack_number
            }
            # # Find the maximum in-order sequence number
            # latest_in_order_seq = -1  # Start with -1 to increment to 0 with the first segment

            # for seg in self.received_data[segment.job_id][segment.connection_id]:
            #     if seg.seq == latest_in_order_seq + 1:
            #         latest_in_order_seq = seg.seq
            #     else:
            #         break

            # # Increment the latest in-order sequence to represent the next expected sequence number
            # latest_in_order_seq += 1
            

            # print(f"Updated latest_in_order_seq: {latest_in_order_seq-1} for job {segment.job_id} and connection {segment.connection_id}")

            # return latest_in_order_seq

