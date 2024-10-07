import simpy

def handle_fifo(router, packet_info):
    """Handle packet processing with FIFO logic within the router."""
    if len(router.queue.items) < router.queue_limit:
        router.queue.put(packet_info)
        router.record_load()
    else:
        print(f"Router {router.router_id} at {router.env.now}: Queue is full. Dropping packet {packet_info['packet']}")

class RouterFifo:
    def __init__(self, env, router_id, nic_speed, delay, queue_limit=1000):
        self.env = env
        self.router_id = router_id
        self.nic_speed = nic_speed
        self.delay = delay  # simulate one-way-delay
        self.queue_limit = queue_limit  # Set the queue size limit
        self.queue = simpy.Store(env)
        self.routing_table = {}  # Maps destination objects to their next hop and NIC speed
        self.load_history = []  # Track load over time
        self.packet_wait_times = []  # List to hold (time, wait_time)
        self.env.process(self.process_packets())  # Recurring calling for popping and forwarding packets

    def record_load(self):
        """Record the current queue length and simulation time."""
        self.load_history.append((self.env.now, len(self.queue.items)))

    def send_packet(self, packet):
        """Route packets based on the routing table."""
        destination = packet.destination
        if destination in self.routing_table:
            next_hop, next_hop_nic_speed = self.routing_table[destination]
            print(f"Router {self.router_id} at {self.env.now}: Routing packet to destination {destination.router_id if hasattr(destination, 'router_id') else id(destination)} via {next_hop.router_id if hasattr(next_hop, 'router_id') else 'direct'}")
            self.record_load()  # Record load before sending
            yield self.env.timeout(self.calculate_transfer_time(packet, next_hop_nic_speed))  # Simulate transfer time based on the packet size and NIC speed
            # yield self.env.process(next_hop.receive_packet(packet) if next_hop else destination.receive_packet(packet))
            if hasattr(destination, 'router_id'):
                if hasattr(next_hop, 'receive_packet') and callable(next_hop.receive_packet):
                    yield self.env.process(next_hop.receive_packet(packet))
                else:
                    print(f"Error: next_hop does not have a valid receive_packet method.")
            else:
                if hasattr(destination, 'receive_packet') and callable(destination.receive_packet):
                    yield self.env.process(destination.receive_packet(packet))
                else:
                    print(f"Error: destination does not have a valid receive_packet method.")

        else:
            print(f"Router {self.router_id} at {self.env.now}: No route to destination {destination.router_id if hasattr(destination, 'router_id') else id(destination)} found.")

    def process_packets(self):
        """Handle packets from ingress to egress with simulated delay and NIC speed."""
        while True:
            self.record_load()  # Record load periodically
            if self.queue.items:
                packet_info = yield self.queue.get()
                packet = packet_info['packet']
                self.record_load()
            
                
                packet_wait_time = self.env.now - packet_info['time_queued']
                self.packet_wait_times.append((self.env.now, packet_wait_time))

                print(f"Router {self.router_id} at {self.env.now}: processing packet {packet}")
                yield self.env.process(self.send_packet(packet))
            else:
                yield self.env.timeout(0.1)  # Wait for packets

    def calculate_transfer_time(self, packet, next_hop_nic_speed):
        """Calculate the transfer time based on the router's NIC speed and the next hop's NIC speed."""
        transfer_speed = min(self.nic_speed, next_hop_nic_speed)
        transfer_time = packet.packet_size / transfer_speed
        return transfer_time + self.delay # Adding delay as a one-way-delay to simulate link travel time

    def add_route(self, destination, via=None):
        """Adds a route to another device (router, processor, DTN). Optionally via another router."""
        next_hop = via if via else destination
        next_hop_nic_speed = next_hop.nic_speed if hasattr(next_hop, 'nic_speed') else self.nic_speed
        self.routing_table[destination] = (next_hop, next_hop_nic_speed)

    def receive_packet(self, packet):
        """Receive packet and record its queue time."""
        print(f"Router {self.router_id} at {self.env.now}: Received packet {packet}")
        packet_info = {'packet': packet, 'time_queued': self.env.now}

        # Call FIFO logic here instead of direct placement
        handle_fifo(self, packet_info)

    def should_drop_packet(self, packet):
        """Determine if a packet should be dropped - currently, always false."""
        return False
