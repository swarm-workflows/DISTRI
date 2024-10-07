import simpy
import random
from entities.packet import Packet
from collections import defaultdict
from protocols.tcp import TCPConnection, TCPSegment
import itertools  # For generating unique IDs

class DTN:
    _id_counter = itertools.count(0)  # Class-level ID generator

    def __init__(self, env, routers, nic_speed, tcp_connections, cca='reno', dtn_data_request=False):
        self.env = env
        self.dtn_id = next(DTN._id_counter)  # Assign a unique ID to each DTN instance
        self.data_store = simpy.Store(env)  # Store for outgoing data
        self.completed_jobs = 0
        self.nic_speed = nic_speed  # Rate of data reception in Mbps
        self.connections = defaultdict(lambda: defaultdict(list))  # Dictionary to store connections per job ID and connection ID
        self.tcp_connections = tcp_connections  # Reference to the global list of TCP connections
        self.cca = cca  # Congestion control algorithm
        self.received_data = defaultdict(lambda: defaultdict(list))  # Store received data segments for each job and connection
        self.expected_seq = defaultdict(lambda: defaultdict(int))  # Track the expected sequence number for each job and connection
        self.routers = {}  # Connecting DTN to all routers with their NIC speeds
        self.edge_router = None   # Connecting DTN to all routers with their NIC speeds
        self.dtn_data_request = dtn_data_request   # Should DTNs request data from other DTNs or not
        self.data_preparation_times = {}  # Job ID to data preparation time
        self.all_dtns = []  # List of all DTNs for inter-DTN data requests (initially empty)
        self.expected_seq = defaultdict(lambda: defaultdict(int))  # Track the expected sequence number for each job and connection
        self.waiting_jobs_for_data = []  # Jobs waiting for data

        # Connect DTN to each router
        for router in routers:
            self.routers[router] = router.nic_speed
            router.add_route(self)  # Ensure DTN is connected to each router
            print(f"DTN {self.dtn_id} initialized with NIC speed {self.nic_speed} Mbps, connecting to router {router.router_id}")

        self.edge_router = routers[-1]
        print(f"DTN {self.dtn_id} initialized with edge router {self.edge_router.router_id}, having NIC speed {self.edge_router.nic_speed} Mbps")

    def set_dtn_list(self, all_dtns):
        """Sets the list of all DTNs."""
        self.all_dtns = all_dtns
        print(f"DTN {self.dtn_id} received the list of DTNs: {[d.dtn_id for d in all_dtns]}")


    def establish_connection(self, processor, job_id):
        """Establishes a TCP connection between DTN and a processor for a specific job."""
        connection = TCPConnection(self.env, self, processor, self.nic_speed, processor.nic_speed, self.routers, self.cca)
        self.connections[job_id][connection.connection_id] = connection
        self.tcp_connections.append(connection)  # Add the new connection to the global list
        print(f"DTN {self.dtn_id} established connection {connection.connection_id} for job {job_id} with Processor {processor.processor_id}")
        return connection


    def send_data(self, processor, data_volume, job_id):
        """Sends data to the requesting processor via a TCP connection."""
        connection = self.establish_connection(processor, job_id)
        print(f"DTN {self.dtn_id} sending {data_volume} Mb of data for job {job_id}")
        yield self.env.process(connection.send_data(data_volume, job_id, 'DATA'))


    def receive_packet(self, packet):
        """Processes incoming data requests from processors, DTNs, and TCP segments."""
        # Handle data requests from processors
        if packet.segment_flag == 'REQUEST':
            print(f"DTN {self.dtn_id} received data request for job {packet.job_id} from Processor {packet.source.processor_id}")
            job_id = packet.job_id
            data_volume = packet.data_volume
            processor = packet.source
            request_time = self.env.now
            self.data_preparation_times[job_id] = {'request_time': request_time, 'start_preparation_time': None, 'end_preparation_time': None}
            packet.connection.close()
            yield self.env.process(self.generate_data_for_job(job_id, data_volume, processor))


        # Handle incoming "DTN_DATA_REQUEST" from other DTNs
        elif packet.segment_flag == "DTN_DATA_REQUEST":
            print(f"DTN {self.dtn_id} received DTN data request for job {packet.job_id} from DTN {packet.source.dtn_id}")
            request_time = self.env.now
            self.data_preparation_times[packet.job_id] = {'request_time': request_time, 'start_preparation_time': None, 'end_preparation_time': None}
            packet.connection.close()
            yield self.env.process(self.generate_dtn_data_for_job(packet.job_id, packet.data_volume, packet.source))  # Simulate data generation and send it back

        # Handle TCP segments
        elif packet.packet_type == 'tcp_segment':
            print(f"DTN {self.dtn_id} received TCP segment {packet.segment_seq} for job {packet.job_id} with connection id {packet.connection_id} at {self.env.now}")
            self.connections[packet.job_id][packet.connection_id] = packet.connection
            segment = TCPSegment(seq=packet.segment_seq, ack=packet.segment_ack, flags=packet.segment_flag, job_id=packet.job_id, connection_id=packet.connection_id, data=packet.data, data_volume=packet.data_volume, missing_segments=packet.missing_segments)
            yield self.env.process(self.connections[packet.job_id][packet.connection_id].receive_segment(segment))

        else:
            print(f"Receiving packet {packet}")
            # Ensure there is some yield or process simulation inside
            yield self.env.timeout(0)  # Simulate packet processing


    def generate_data_for_job(self, job_id, data_volume, processor):
        """Simulates data generation and sends the data back to the requesting processor or another DTN."""
        # Randomly decide if the data will be generated locally or requested from another DTN
        if random.random() < 0.30 and len(self.all_dtns) > 1 and self.dtn_data_request:
            # 30% chance to request data from another DTN
            start_preparation_time = self.env.now
            self.data_preparation_times[job_id]['start_preparation_time'] = start_preparation_time
            other_dtn = random.choice([dtn for dtn in self.all_dtns if dtn != self])
            print(f"DTN {self.dtn_id} requesting data from DTN {other_dtn.dtn_id} for job {job_id}")
            data_event = self.env.event()
            self.waiting_jobs_for_data.append((job_id, data_event))
            yield self.env.process(self.send_data_request_to_dtn(other_dtn, job_id, data_volume))
            yield data_event  # Wait here until the data arrives
            end_preparation_time = self.env.now
            self.data_preparation_times[job_id]['end_preparation_time'] = end_preparation_time
            print(f"DTN {self.dtn_id} received {data_volume} Mb of data for job {job_id} from DTN {other_dtn.dtn_id} at {end_preparation_time}, after {end_preparation_time - start_preparation_time} seconds for processor {processor.processor_id}")
            yield self.env.process(self.send_data(processor, data_volume, job_id))
        else:
            # 70% chance to generate data locally
            print(f"DTN {self.dtn_id} will generate data locally for job {job_id}")
            start_preparation_time = self.env.now
            if not self.dtn_data_request:    # No delay for local generation, however, when not taking data using other DTN, introduce delay to reflect data transfer       
                preparation_time = data_volume / (self.nic_speed / 2)  # Assume it takes the data from the outside world at a rate half of its NIC speed
                print(f"DTN {self.dtn_id} preparing data for job {job_id}")
                yield self.env.timeout(preparation_time)  # Simulate the time needed to prepare data
            end_preparation_time = self.env.now
            self.data_preparation_times[job_id]['start_preparation_time'] = start_preparation_time
            self.data_preparation_times[job_id]['end_preparation_time'] = end_preparation_time
            print(f"DTN {self.dtn_id} generated {data_volume} Mb of data for job {job_id} at {end_preparation_time}, after {end_preparation_time - start_preparation_time} seconds for processor {processor.processor_id}")
            yield self.env.process(self.send_data(processor, data_volume, job_id))

    def send_data_request_to_dtn(self, other_dtn, job_id, data_volume):
        """Sends a data request to another DTN for the requested data."""
        connection = TCPConnection(self.env, self, other_dtn, self.nic_speed, other_dtn.nic_speed, self.routers, self.cca)
        self.connections[job_id][connection.connection_id] = connection
        self.tcp_connections.append(connection)  # Add the new connection to the global list
        print(f"DTN {self.dtn_id} sending DTN_DATA_REQUEST for {data_volume} Mb of data to DTN {other_dtn.dtn_id} for job {job_id}")
        yield self.env.process(connection.send_data(data_volume, job_id, 'DTN_DATA_REQUEST'))

    def generate_dtn_data_for_job(self, job_id, data_volume, other_dtn):
        """Simulates data generation and sends the data back to the requesting processor."""
        start_preparation_time = self.env.now
        preparation_time = data_volume / (self.nic_speed / 2)  # Assume it takes the data from the outside world at a rate half of its NIC speed
        print(f"DTN {self.dtn_id} preparing data for job {job_id} requested by DTN {other_dtn.dtn_id}")
        yield self.env.timeout(preparation_time)  # Simulate the time needed to prepare data
        end_preparation_time = self.env.now
        self.data_preparation_times[job_id]['start_preparation_time'] = start_preparation_time
        self.data_preparation_times[job_id]['end_preparation_time'] = end_preparation_time
        print(f"DTN {self.dtn_id} generated {data_volume} Mb of data for job {job_id} at {end_preparation_time}, after {preparation_time} seconds for another DTN {other_dtn.dtn_id}")
        yield self.env.process(self.send_data_to_dtn(other_dtn, data_volume, job_id))

    def send_data_to_dtn(self, other_dtn, data_volume, job_id):
        """Sends a data request to another DTN for the requested data."""
        connection = TCPConnection(self.env, self, other_dtn, self.nic_speed, other_dtn.nic_speed, self.routers, self.cca)
        self.connections[job_id][connection.connection_id] = connection
        self.tcp_connections.append(connection)  # Add the new connection to the global list
        print(f"DTN {self.dtn_id} sending {data_volume} Mb of DATA to DTN {other_dtn.dtn_id} for job {job_id}")
        yield self.env.process(connection.send_data(data_volume, job_id, 'DATA'))

    def receive_segment(self, segment):
        print(f"DTN {self.dtn_id} received segment {segment.flags} for job {segment.job_id} with connection id {segment.connection_id} at {self.env.now}")

        if segment.flags == 'FIN':
            print(f"DTN {self.dtn_id} completed receiving data request for job {segment.job_id}")
            self.receive_data_sent_flag(segment.job_id)  # Assuming this method exists to mark job as done
            # Check if the connection exists and close it if necessary
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
                print(f"DTN {self.dtn_id} initialized received_data for job {segment.job_id}")

            if segment.connection_id not in self.received_data[segment.job_id]:
                self.received_data[segment.job_id][segment.connection_id] = []
                print(f"DTN {self.dtn_id} initialized received_data for connection {segment.connection_id} in job {segment.job_id}")

            # Check for duplicates before appending
            if segment.seq not in [seg.seq for seg in self.received_data[segment.job_id][segment.connection_id]]:
                self.received_data[segment.job_id][segment.connection_id].append(segment)

            # Ensure segments are stored in ascending order of sequence numbers
            self.received_data[segment.job_id][segment.connection_id].sort(key=lambda x: x.seq)

            # Print received data after sorting
            # print(f"Received data after sorting: {[seg.seq for seg in self.received_data[segment.job_id][segment.connection_id]]}")

            # Find missing segments and determine the next ACK number
            missing_segments = []
            expected_seq = self.expected_seq[segment.job_id][segment.connection_id]  # Track expected sequence number
            ack_number = None  # Acknowledgment number to be sent back

            for seg in self.received_data[segment.job_id][segment.connection_id]:
                if seg.seq == expected_seq:
                    expected_seq += 1
                else:
                    # If a segment is missing, track it
                    for missing_seq in range(expected_seq, seg.seq):
                        if ack_number is None:
                            ack_number = missing_seq + 1
                        missing_segments.append(missing_seq)
                    expected_seq = seg.seq + 1

            if ack_number is None:
                ack_number = expected_seq  # If no missing segments, acknowledge the next expected sequence

            # Update the expected sequence for future segments
            self.expected_seq[segment.job_id][segment.connection_id] = expected_seq

            print(f"DTN {self.dtn_id} missing segments: {missing_segments}")
            print(f"DTN {self.dtn_id} ACK number: {ack_number}")

            # Return the missing segments and the ACK number for retransmission or acknowledgment
            return {
                "missing_segments": missing_segments,
                "ack_number": ack_number
            }

    def receive_data_sent_flag(self, job_id):
        """ Handles reception of the data sent flag from the DTN. """
        for job, event in self.waiting_jobs_for_data:
            if job == job_id:
                event.succeed()
                self.waiting_jobs_for_data.remove((job, event))
                break