import simpy

class RouterFq:
    def __init__(self, env, router_id, nic_speed, delay, queue_limit=1000):
        self.env = env
        self.router_id = router_id
        self.nic_speed = nic_speed
        self.delay = delay
        self.queue_limit = queue_limit  # Total queue size limit
        self.queues = {}  # Maps destination objects to queues
        self.queue_ids = {}  # Maps destination objects to custom queue IDs
        self.routing_table = {}  # Maps destination objects to their next hop and NIC speed
        self.load_history = []  # Track load over time
        self.packet_wait_times = []  # List to hold (time, wait_time)
        self.limit_per_queue = queue_limit  # Initially set to total limit, will be adjusted

    def record_load(self, queue_id):
        """Record the current queue length and simulation time for the given queue."""
        queue_length = len(self.queues[queue_id].items)
        self.load_history.append((self.env.now, queue_id, queue_length))

    def send_packet(self, packet):
        """Send the packet to the destination via the routing table."""
        next_hop, next_hop_nic_speed = self.routing_table.get(packet.destination)
        yield self.env.timeout(self.calculate_transfer_time(packet, next_hop_nic_speed))
        if next_hop:
            yield self.env.process(next_hop.receive_packet(packet))
        else:
            print(f"Router {self.router_id}: No next hop for packet destined to {packet.destination}.")

    def process_queue(self, queue_id):
        """Process packets from a specific destination queue."""
        while True:
            self.record_load(queue_id)  # Record load periodically
            if self.queues[queue_id].items:
                print(f"Router {self.router_id}: Retrieving packet for destination {queue_id}. Queue size is now {len(self.queues[queue_id].items)}")
                packet_info = yield self.queues[queue_id].get()
                self.record_load(queue_id)  # Record load periodically
                packet = packet_info['packet']
                print(f"Router {self.router_id}: Retrieved packet {packet} for destination {queue_id}. Queue size is now {len(self.queues[queue_id].items)}")

                packet_wait_time = self.env.now - packet_info['time_queued']
                self.packet_wait_times.append((self.env.now, packet_wait_time))

                print(f"Router {self.router_id}: Processing packet {packet}. Preparing to send to next hop or destination.")
                yield self.env.process(self.send_packet(packet))
            else:
                yield self.env.timeout(0.1)  # Idle wait

    def calculate_transfer_time(self, packet, next_hop_nic_speed):
        """Calculate the transfer time based on the router's NIC speed and the next hop's NIC speed."""
        transfer_speed = min(self.nic_speed, next_hop_nic_speed)
        transfer_time = packet.packet_size / transfer_speed
        print(f"Router {self.router_id}: Calculated transfer time {transfer_time} for packet size {packet.packet_size}")
        return transfer_time + self.delay  # Adding delay as an one-way-delay to simulate link travel time

    def adjust_queue_limits(self):
        """Adjust the queue limits dynamically whenever a new route is added."""
        if self.queues:
            num_queues = len(self.queues)
            self.limit_per_queue = self.queue_limit // num_queues  # Divide the total limit equally among all queues
            print(f"Router {self.router_id}: New number of queues = {num_queues}, and queue size = {self.limit_per_queue}")

    def add_route(self, destination, via=None, queue_id=None):
        """Adds a route to another device (router, processor, DTN), optionally via another router."""
        via = None
        next_hop = via if via else destination
        next_hop_nic_speed = next_hop.nic_speed if hasattr(next_hop, 'nic_speed') else self.nic_speed

        if via is None:
            # Create a queue only if the connection is direct
            if queue_id is None:
                queue_id = len(self.queue_ids) + 1  # Auto-increment queue_id if not provided
        
            self.routing_table[destination] = (next_hop, next_hop_nic_speed)
            self.queue_ids[destination] = queue_id
            self.queues[queue_id] = simpy.Store(self.env)  # Initialize a queue for this route
            self.env.process(self.process_queue(queue_id))  # Start a process for handling this queue
            print(f"Router {self.router_id}: Added direct route to {destination.router_id if hasattr(destination, 'router_id') else 'unknown'}, queue_id: {queue_id}, next hop NIC speed: {next_hop_nic_speed}")
        else:
            # For non-direct routes (via another router), do not create a new queue
            self.routing_table[destination] = (next_hop, next_hop_nic_speed)
            print(f"Router {self.router_id}: Added route to {destination.router_id if hasattr(destination, 'router_id') else 'unknown'} via {via.router_id if hasattr(via, 'router_id') else 'unknown'}, no new queue created")
        
        # Adjust queue limits after adding a new route
        self.adjust_queue_limits()

    def receive_packet(self, packet):
        """Receive a packet and route it to the appropriate queue based on the next hop determined by the routing table."""
        print(f"Router {self.router_id}: Received packet {packet}")
        if packet.destination in self.queue_ids:
            queue_id = self.queue_ids[packet.destination]
            print(f"Router {self.router_id}: Enqueue packet to queue for destination {packet.destination} via queue_id {queue_id}.")
            if len(self.queues[queue_id].items) < self.limit_per_queue:
                self.queues[queue_id].put({'packet': packet, 'time_queued': self.env.now})
                self.record_load(queue_id)  # Updated to use queue_id
            else:
                print(f"Router {self.router_id}: Queue for destination {packet.destination} is full. Dropping packet.")
        else:
            print(f"Router {self.router_id}: No route to destination {packet.destination}. Dropping packet.")

    def should_drop_packet(self, packet):
        """Determine if a packet should be dropped - currently, always false."""
        return False