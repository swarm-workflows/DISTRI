import simpy
from entities.packet import Packet
from collections import defaultdict
from protocols.tcp import TCPConnection, TCPSegment

class DTN:
    def __init__(self, env, routers, nic_speed, tcp_connections, cca='reno'):
        self.env = env
        self.data_store = simpy.Store(env)  # Store for outgoing data
        self.completed_tasks = 0
        self.nic_speed = nic_speed  # Rate of data reception in Gbps
        self.connections = defaultdict(lambda: defaultdict(list))  # Dictionary to store connections per task ID and connection ID
        self.tcp_connections = tcp_connections  # Reference to the global list of TCP connections
        self.cca = cca  # Congestion control algorithm
        self.received_data = defaultdict(lambda: defaultdict(list))  # Store received data segments for each task and connection
        self.expected_seq = defaultdict(lambda: defaultdict(int))  # Track the expected sequence number for each task and connection
        self.routers = {}  # Connecting DTN to all routers with their NIC speeds
        self.data_preparation_times = {}  # Task ID to data preparation time

        for router in routers:
            self.routers[router] = router.nic_speed
            router.add_route(self)  # Ensure DTN is connected to each router

    def establish_connection(self, processor, task_id):
        connection = TCPConnection(self.env, self, processor, self.nic_speed, processor.nic_speed, self.routers, self.cca)
        self.connections[task_id][connection.connection_id] = connection
        self.tcp_connections.append(connection)  # Add the new connection to the global list
        return connection


    def receive_segment(self, segment):
        print(f"Processor received segment {segment.flags} for task {segment.task_id} with connection id {segment.connection_id} at {self.env.now}")

        if segment.flags == 'FIN':
            print(f"Processor completed receiving data request for task {segment.task_id}")
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
            print(f"Received data before sorting: {[seg.seq for seg in self.received_data[segment.task_id][segment.connection_id]]}")


            # Ensure segments are stored in ascending order of sequence numbers
            self.received_data[segment.task_id][segment.connection_id].sort(key=lambda x: x.seq)

            # Print received data after sorting
            print(f"Received data after sorting: {[seg.seq for seg in self.received_data[segment.task_id][segment.connection_id]]}")

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

            print(f"Missing segments: {missing_segments}")
            print(f"ACK number: {ack_number}")

            return {
                "missing_segments": missing_segments,
                "ack_number": ack_number
            }
        


            # # Find the maximum in-order sequence number
            # latest_in_order_seq = 0
            # for i, seg in enumerate(self.received_data[segment.task_id][segment.connection_id]):
            #     if i == 0 or self.received_data[segment.task_id][segment.connection_id][i].seq == self.received_data[segment.task_id][segment.connection_id][i - 1].seq + 1:
            #         latest_in_order_seq = seg.seq + 1
            #     else:
            #         break

            # print(f"Updated latest_in_order_seq: {latest_in_order_seq} for task {segment.task_id} and connection {segment.connection_id}")

            # return latest_in_order_seq



    def send_data(self, processor, data_volume, task_id):
        connection = self.establish_connection(processor, task_id)
        yield self.env.process(connection.send_data(data_volume, task_id, 'DATA'))


    def receive_packet(self, packet):
        """Processes data requests from processors and sends the required data."""
        if packet.segment_flag == 'REQUEST':
            print(f"DTN received data request for task {packet.task_id} from Processor {packet.source.processor_id}")
            task_id = packet.task_id
            data_volume = packet.data_volume
            processor = packet.source
            request_time = self.env.now
            self.data_preparation_times[task_id] = {'request_time': request_time, 'start_preparation_time': None, 'end_preparation_time': None}
            yield self.env.process(self.generate_data_for_task(task_id, data_volume, processor))
        if packet.packet_type == 'tcp_segment':
            print(f"DTN received TCP segment {packet.segment_seq} for task {packet.task_id} with connection id {packet.connection_id} at {self.env.now}")
            self.connections[packet.task_id][packet.connection_id] = packet.connection
            segment = TCPSegment(seq=packet.segment_seq, ack=packet.segment_ack, flags=packet.segment_flag, task_id=packet.task_id, connection_id=packet.connection_id, data=packet.data, data_volume=packet.data_volume, missing_segments=packet.missing_segments)
            yield self.env.process(self.connections[packet.task_id][packet.connection_id].receive_segment(segment))

            # if packet.task_id in self.connections and packet.connection_id in self.connections[packet.task_id]:
            #     if self.connections[packet.task_id][packet.connection_id].state != 'CLOSED':
            #         segment = TCPSegment(seq=packet.segment_seq, flags=packet.segment_flag, task_id=packet.task_id, data=packet.packet_size, data_volume=packet.data_volume)
            #         # self.receive_segment(segment)
            #         self.connections[packet.task_id][packet.connection_id].receive_segment(segment)



    def generate_data_for_task(self, task_id, data_volume, processor):
        """Generates data based on the request and sends it back to the requesting processor."""
        start_preparation_time = self.env.now
        preparation_time = data_volume / (self.nic_speed / 2)  # Assume it takes the data from the outside world at a rate half of its NIC speed
        print(f"DTN preparing data for task {task_id}")
        yield self.env.timeout(preparation_time)  # Simulate the time needed to prepare data
        end_preparation_time = self.env.now
        self.data_preparation_times[task_id]['start_preparation_time'] = start_preparation_time
        self.data_preparation_times[task_id]['end_preparation_time'] = end_preparation_time
        print(f"DTN generated {data_volume} Gb of data for task {task_id} at {end_preparation_time}, after {preparation_time} seconds for processor {processor.processor_id}")
        yield self.env.process(self.send_data(processor, data_volume, task_id))
