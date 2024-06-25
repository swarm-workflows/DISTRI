import simpy
from entities.packet import Packet

class DTN:
    def __init__(self, env, routers, nic_speed):
        self.env = env
        self.data_store = simpy.Store(env)  # Store for outgoing data
        self.completed_tasks = 0
        self.nic_speed = nic_speed  # Rate of data reception in Gbps
        self.routers = {}  # Connecting DTN to all routers with their NIC speeds
        self.data_preparation_times = {}  # Task ID to data preparation time

        for router in routers:
            self.routers[router] = router.nic_speed
            router.add_route(self)  # Ensure DTN is connected to each router

    def receive_packet(self, packet):
        """Processes data requests from processors and sends the required data."""
        if packet.packet_type == 'data_request':
            print(f"DTN received data request for task {packet.task_id} from Processor {packet.source.processor_id}")
            task_id = packet.task_id
            data_volume = packet.data_volume
            processor = packet.source
            request_time = self.env.now
            self.data_preparation_times[task_id] = {'request_time': request_time, 'start_preparation_time': None, 'end_preparation_time': None}
            self.env.process(self.generate_data_for_task(task_id, data_volume, processor))

    def generate_data_for_task(self, task_id, data_volume, processor):
        """Generates data based on the request and sends it back to the requesting processor."""
        start_preparation_time = self.env.now
        preparation_time = data_volume / (self.nic_speed / 2) # Assume it takes the data from the outside world at a rate half of its NIC speed
        print(f"DTN preparing data for task {task_id}")
        yield self.env.timeout(preparation_time)  # Simulate the time needed to prepare data
        end_preparation_time = self.env.now
        self.data_preparation_times[task_id]['start_preparation_time'] = start_preparation_time
        self.data_preparation_times[task_id]['end_preparation_time'] = end_preparation_time
        print(f"DTN generated {data_volume} Gb of data for task {task_id} at {end_preparation_time}, after {preparation_time} seconds for processor {processor.processor_id}")
        self.env.process(self.send_data_to_processor(task_id, data_volume, processor))

    def send_data_to_processor(self, task_id, data_volume, processor):
        """Sends prepared data to the processor through the appropriate router and signals completion."""
        data_packet = Packet(
            source=self,
            destination=processor,
            packet_type='data',
            packet_size=data_volume,
            task_id=task_id
        )

        print(f"DTN is searching routers for sending {data_volume} Gb of data for task {task_id} to processor {processor.processor_id}")
        # Send the actual data
        for router, router_nic_speed in self.routers.items():
            if router == processor.router:
                print(f"DTN is sending {data_volume} Gb of data for task {task_id} for processor {processor.processor_id} via router {router.router_id}")
                transfer_speed = min(self.nic_speed, router_nic_speed)
                yield self.env.timeout(data_volume / transfer_speed)    # Simulate data transmission delay based on data volume
                router.receive_packet(data_packet)
                break

        completion_flag = Packet(
            source=self,
            destination=processor,
            packet_type='data_complete',
            task_id=task_id
        )

        for router in self.routers:
            if router == processor.router:
                print(f"DTN is sending transfer complete message for {data_volume} Gb of data for task {task_id} for processor {processor.processor_id} via router {router.router_id}")
                router.receive_packet(completion_flag)  # Send the completion flag through the router
                break