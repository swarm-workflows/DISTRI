from collections import deque
from entities.packet import Packet
from protocols.helpers.tcp_segments import TCPSegment
from protocols.reno import Reno
from protocols.cubic import Cubic
from protocols.htcp import HTCP
import pandas as pd
import random

class TCPConnection:
    def __init__(self, env, src, dst, src_nic_speed, dst_nic_speed, routers, cca='reno'):
        self.env = env
        self.src = src
        self.dst = dst
        self.state = 'OPEN'
        self.snd_una = 0  # Send unacknowledged
        self.snd_nxt = 0  # Send next
        self.rcv_nxt = 0  # Receive next
        self.cwnd = 1  # Congestion window
        self.ssthresh = 64  # Slow start threshold
        self.rtt = 1  # Round-trip time
        self.srtt = None  # Smoothed RTT
        self.rttvar = None  # RTT Variance
        self.rto = 1  # Initial RTO
        self.segments = deque()
        self.num_full_segments = 0
        self.num_total_segments = 0
        self.remaining_Mbytes = 0
        self.src_nic_speed = src_nic_speed
        self.dst_nic_speed = dst_nic_speed
        self.routers = routers
        self.cca = self.set_cca(cca)
        self.received_data = {}  # Dictionary to store received data segments
        self.connection_id = self.generate_unique_connection_id()
        self.retransmissions = 0
        self.retransmission_log = pd.DataFrame(columns=['time', 'retransmissions'])
        self.rtt_log = pd.DataFrame(columns=['time', 'rtt'])
        self.send_times = {}
        self.duplicate_acks = 0
        self.last_ack = 0
        self.recovery_segment_seq = 0
        self.missing_segments = []  # List of missing segments for selective repeat
        self.data_acknowledged_thpt = 0
        self.data_acknowledged_gdpt = 0
        self.throughput_log = pd.DataFrame(columns=['time', 'throughput', 'connection_id', 'src', 'dst'])
        self.goodput_log = pd.DataFrame(columns=['time', 'goodput', 'connection_id', 'src', 'dst'])
        self.cwnd_log = pd.DataFrame(columns=['time', 'cwnd', 'connection_id', 'src', 'dst'])
        self.env.process(self.log_throughput())
        self.env.process(self.log_goodput())
        print(f"TCPConnection {self} initialized between src: {self.src} and dst: {self.dst} with connection id {self.connection_id} and CCA {cca}")

    def generate_unique_connection_id(self):
        return random.randint(1000, 99999)  # Generate a unique integer ID between 1000 and 99999

    def set_cca(self, cca_name):
        if cca_name == 'reno':
            return Reno(self)
        elif cca_name == 'cubic':
            return Cubic(self)
        elif cca_name == 'htcp':
            return HTCP(self)
        else:
            raise ValueError('Unsupported CCA')

    def send_segment(self, task_id, seq, ack=None, flags=None, data=0, data_volume=0):
        if self.state != 'CLOSED':
            segment = TCPSegment(seq, ack, flags, task_id=task_id, connection_id=self.connection_id, data_volume=data_volume, data=data)
            segment.send_time = self.env.now  # Record the send time
            self.send_times[seq] = self.env.now  # Keep track of send times by sequence number
            self.segments.append(segment)
            print(f"TCP {self.connection_id} at {self.env.now}: Prepared segment {flags} for task {task_id} with seq {seq}")
            yield self.env.process(self._send_segment(segment))
            # yield self._send_segment(segment)         

    def _send_segment(self, segment):
        print(f"TCP {self.connection_id} at {self.env.now}: Sending segment {segment.flags} with seq {segment.seq} from {self.src} to {self.dst} for task {segment.task_id}")
        # Simulate network transmission delay
        yield self.env.timeout(segment.data / self.src_nic_speed)
        print(f"TCP {self.connection_id} at {self.env.now}: Finally Sending segment {segment.flags} with seq {segment.seq} from {self.src} to {self.dst} for task {segment.task_id}")
        self.route_segment(segment)
        if segment.flags != 'ACK' and segment.flags != 'FIN' and self.state != 'RECOVERY' and self.state != 'CLOSED':
            self.env.process(self.check_timeout(segment.seq))  # Start timeout check

    def check_timeout(self, seq):
        def timeout_check():
            yield self.env.timeout(self.rto)  # Wait for RTO duration
            if seq >= self.snd_una and self.state != 'CLOSED':
                print(f"TCP {self.connection_id} at {self.env.now}: Timeout detected for seq {seq}")
                self.cca.on_loss(is_timeout=True)   # Notify the CCA of the timeout and set CWND accordingly
                for segment in self.segments:
                    if segment.seq == seq:
                        # print(f"TCP {self.connection_id} at {self.env.now}: Retransmitting missing segment {segment.seq} with flag {segment.flags} for task {segment.task_id}")
                        yield self.env.process(self._send_segment(segment))  # Yielding to ensure the process waits for retransmission
                        # Log data rate
                        self.data_acknowledged_thpt += segment.data_volume            
                        self.log_throughput()
                        self.retransmissions = segment.seq - self.snd_una
                        self.retransmission_log = pd.concat([self.retransmission_log, pd.DataFrame({'time': [self.env.now], 'retransmissions': [self.retransmissions], 'connection_id': [self.connection_id], 'src': [self.src], 'dst': [self.dst]})], ignore_index=True)
                        break

        return timeout_check()  # Return the generator

    def route_segment(self, segment):
        """ Routes the segment through the appropriate router """
        from entities.processor import Processor
        if isinstance(self.src, Processor):
            router = self.src.router
        else:
            router = next((r for r in self.routers if r.router_id == self.dst.router.router_id), None)

        if router:
            if segment.flags == 'ACK':
                print(f"Routing segment {segment.seq} with flag {segment.flags} for task {segment.task_id} via Router {router.router_id}")
                packet = Packet(
                    source=self.dst,
                    destination=self.src,
                    packet_type='tcp_segment',
                    packet_size=segment.data,
                    segment_seq=segment.seq,
                    segment_flag=segment.flags,
                    segment_ack=segment.ack,
                    task_id=segment.task_id,
                    data=segment.data,
                    data_volume=segment.data_volume,
                    connection_id=segment.connection_id,
                    connection=self,
                    missing_segments=segment.missing_segments
                )
            else:
                print(f"Routing segment {segment.seq} with flag {segment.flags} for task {segment.task_id} via Router {router.router_id}")
                packet = Packet(
                    source=self.src,
                    destination=self.dst,
                    packet_type='tcp_segment',
                    packet_size=segment.data,
                    segment_seq=segment.seq,
                    segment_flag=segment.flags,
                    segment_ack=segment.ack,
                    task_id=segment.task_id,
                    data=segment.data,
                    data_volume=segment.data_volume,
                    connection_id=segment.connection_id,
                    connection=self,
                    missing_segments=segment.missing_segments
                )
            router.receive_packet(packet)

    def _wait_for_acks(self, task_id, total_segments):
        while self.snd_una < total_segments and self.state != 'CLOSED':
            yield self.env.timeout(1)
        yield self.env.process(self.send_segment(task_id=task_id, seq=total_segments, ack=0, flags='FIN'))
        self.close()
        print(f"TCP {self.connection_id} at {self.env.now}: Sending FIN for task {task_id} after all data segments are acknowledged")

    def handle_ack(self, segment):
        # Handle received ACK
        # print(f"TCP {self.connection_id} at {self.env.now} with self_una {self.snd_una}: ACK received with ack number {segment.ack}, segment seq {segment.seq}, segments missing segments {segment.missing_segments} and self missing segments {self.missing_segments}")
        
        if segment.seq == self.num_total_segments:
            yield self.env.process(self.send_segment(task_id=segment.task_id, seq=self.num_total_segments, ack=0, flags='FIN'))
            self.close()
            print(f"TCP {self.connection_id} at {self.env.now}: Sending FIN for task {segment.task_id} after all data segments are acknowledged")

        elif segment.ack > self.snd_una and len(self.missing_segments) == 0:
            print(f"TCP {self.connection_id} at {self.env.now}: Processing new ACK with ack number {segment.ack}")
            self.duplicate_acks = 0
            if self.state == 'RECOVERY':
                self.state = 'OPEN'
            self.cca.on_ack()
            self.snd_una = max(self.snd_una, segment.ack)
            yield self.env.process(self._send_data(segment.task_id))
            self.update_rtt(segment.ack)

            # Log data rate
            self.data_acknowledged_thpt += segment.data_volume
            self.data_acknowledged_gdpt += segment.data_volume
            self.log_throughput()
            self.log_goodput()
            print(f"TCP {self.connection_id} at {self.env.now}: data_acked {segment.data_volume}, total_data_acked {self.data_acknowledged_thpt}")

        elif segment.ack == self.snd_una:
            self.duplicate_acks += 1
            print(f"TCP {self.connection_id} at {self.env.now}: Duplicate ACK {self.duplicate_acks} received with ack number {segment.ack}")

            if self.state == 'RECOVERY' and self.duplicate_acks > 3:
                yield self.env.process(self.retransmit(task_id=segment.task_id))
                self.update_rtt(segment.ack)
                self.data_acknowledged_thpt += segment.data_volume
                self.log_throughput()
            
            elif self.duplicate_acks == 3:
                print(f"TCP {self.connection_id} at {self.env.now}: Triple duplicate ACKs received, entering fast recovery and retransmitting segment {self.snd_una}")
                self.recovery_segment_seq = segment.ack
                # print(f"TCP {self.connection_id} at {self.env.now}: Received missing segments list: {segment.missing_segments}")  
                self.missing_segments.extend(seg for seg in segment.missing_segments if seg not in self.missing_segments)
                # print(f"TCP {self.connection_id} at {self.env.now}: Updated self missing segments list: {self.missing_segments}")  
                yield self.env.process(self.retransmit())
                self.update_rtt(segment.ack)
                self.data_acknowledged_thpt += segment.data_volume
                self.log_throughput()
                self.state = 'RECOVERY'
            
            elif len(self.missing_segments) > 0:
                # This condition is entered if there are still missing segments to be handled.
                # print(f"TCP {self.connection_id} at {self.env.now}: Handling missing segments: {self.missing_segments}")
                yield self.env.process(self.retransmit())
                self.update_rtt(segment.ack)   
                self.data_acknowledged_thpt += segment.data_volume
                self.log_throughput()     

        
        elif len(self.missing_segments) > 0:
            # This condition is entered if there are still missing segments to be handled.
            # print(f"TCP {self.connection_id} at {self.env.now}: Handling missing segments: {self.missing_segments}")
            yield self.env.process(self.retransmit())
            self.update_rtt(segment.ack)
            self.data_acknowledged_thpt += segment.data_volume
            self.log_throughput()


    def retransmit_missing_segments(self, retransmit_numbers = 0):
            # Handle retransmission of missing segments
            retransmitted_packets = 0
            segments_to_remove = []

            if self.state != 'CLOSED':
                for seq in self.missing_segments:
                    if retransmitted_packets >= retransmit_numbers:
                        break
                    for segment in self.segments:
                        if segment.seq == seq:
                            print(f"TCP {self.connection_id} at {self.env.now}: Retransmitting missing segment {seq} with flag {segment.flags} for task {segment.task_id}")
                            yield self.env.process(self._send_segment(segment))
                            segments_to_remove.append(seq)
                            retransmitted_packets += 1
                            self.retransmissions = segment.seq - self.snd_una
                            self.retransmission_log = pd.concat([self.retransmission_log, pd.DataFrame({'time': [self.env.now], 'retransmissions': [self.retransmissions], 'connection_id': [self.connection_id], 'src': [self.src], 'dst': [self.dst]})], ignore_index=True)
                            break

            for seq in segments_to_remove:
                self.missing_segments.remove(seq)
            
            if len(self.missing_segments) == 0:
                self.duplicate_acks = 0
                print(f"TCP {self.connection_id} at {self.env.now}: Missing segments sent, resetting duplicate acks  to 0")

    def retransmit(self, task_id = None, is_timeout=False):
        # Handle retransmission
        # print(f"TCP {self.connection_id} at {self.env.now}: Missing segments before retransmission: {self.missing_segments}")    
        retransmitted_packets = 0
        if self.state == 'RECOVERY' and len(self.missing_segments) > 0:
            self.cca.on_recovery()
            yield self.env.process(self._send_data(task_id))
        elif self.state == 'RECOVERY' and len(self.missing_segments) == 0:
            self.cca.on_recovery()
            for segment in self.segments:
                if segment.seq == self.recovery_segment_seq:
                    print(f"TCP {self.connection_id} at {self.env.now}: Retransmitting missing segment {segment.seq} with flag {segment.flags} for task {segment.task_id}")
                    yield self.env.process(self._send_segment(segment))
                    retransmitted_packets += 1
                    self.retransmissions = segment.seq - self.snd_una
                    self.retransmission_log = pd.concat([self.retransmission_log, pd.DataFrame({'time': [self.env.now], 'retransmissions': [self.retransmissions], 'connection_id': [self.connection_id], 'src': [self.src], 'dst': [self.dst]})], ignore_index=True)
                    break
        else:
            self.cca.on_loss(is_timeout)
            yield self.env.process(self.retransmit_missing_segments(retransmit_numbers=1))
        
        # print(f"TCP {self.connection_id} at {self.env.now}: Missing segments after retransmission: {self.missing_segments}")    


    def log_throughput(self):
        while True and self.state != 'CLOSED':
            yield self.env.timeout(1)  # Log throughput every second
            throughput = self.data_acknowledged_thpt / 1  # MBytes per second
            new_entry = pd.DataFrame({
                'time': [self.env.now],
                'throughput': [throughput],
                'connection_id': [self.connection_id],
                'src': [self.src],
                'dst': [self.dst]
            })
            
            # Only concatenate if new_entry is not empty and if throughput_log is not empty
            if not new_entry.empty:
                if self.throughput_log.empty:
                    self.throughput_log = new_entry
                else:
                    self.throughput_log = pd.concat([self.throughput_log, new_entry], ignore_index=True)
                    
            self.data_acknowledged_thpt = 0  # Reset counter

    def log_goodput(self):
        while True and self.state != 'CLOSED':
            yield self.env.timeout(1)  # Log goodput every second
            goodput = self.data_acknowledged_gdpt / 1  # MBytes per second
            new_entry = pd.DataFrame({
                'time': [self.env.now],
                'goodput': [goodput],
                'connection_id': [self.connection_id],
                'src': [self.src],
                'dst': [self.dst]
            })
            
            # Only concatenate if new_entry is not empty and if goodput_log is not empty
            if not new_entry.empty:
                if self.goodput_log.empty:
                    self.goodput_log = new_entry
                else:
                    self.goodput_log = pd.concat([self.goodput_log, new_entry], ignore_index=True)
                    
            self.data_acknowledged_gdpt = 0  # Reset counter


    def log_cwnd(self):
        new_entry = pd.DataFrame({
            'time': [self.env.now],
            'cwnd': [self.cwnd],
            'connection_id': [self.connection_id],
            'src': [self.src],
            'dst': [self.dst]
        })
        
        # Only concatenate if new_entry is not empty and if cwnd_log is not empty
        if not new_entry.empty:
            if self.cwnd_log.empty:
                self.cwnd_log = new_entry
            else:
                self.cwnd_log = pd.concat([self.cwnd_log, new_entry], ignore_index=True)

    def update_cwnd(self, new_cwnd):
        self.cwnd = new_cwnd
        self.log_cwnd()
        print(f"TCP {self.connection_id} at {self.env.now}: new CWND {self.cwnd}")

    def update_rtt(self, ack):
        if ack-1 in self.send_times:
            rtt = self.env.now - self.send_times.pop(ack-1)
            if self.srtt is None:
                self.srtt = rtt
                self.rttvar = rtt / 2
            else:
                self.rttvar = (1 - 0.25) * self.rttvar + 0.25 * abs(self.srtt - rtt)
                self.srtt = (1 - 0.125) * self.srtt + 0.125 * rtt
            self.rto = self.srtt + max(1, 4 * self.rttvar)
            self.rtt_log = pd.concat([self.rtt_log, pd.DataFrame({'time': [self.env.now], 'rtt': [rtt], 'connection_id': [self.connection_id], 'src': [self.src], 'dst': [self.dst]})], ignore_index=True)
            print(f"TCP {self.connection_id} at {self.env.now}: Updated RTT to {rtt}, srtt to {self.srtt}, rttvar to {self.rttvar}, rto to {self.rto}")

    def close(self):
        self.state = 'CLOSED'
        print(f"TCP {self.connection_id} at {self.env.now}: Connection closed from {self.src} to {self.dst}")

    # Ensure to send FIN only after all data segments are acknowledged
    def send_data(self, data_volume, task_id, type='DATA'):
        if type == 'DATA':
            print(f"TCP {self.connection_id} at {self.env.now}: Preparing to send {data_volume} MB of data for task {task_id}")
            self.num_full_segments = data_volume // 1.5  # Assume 1.5 MB per segment
            self.remaining_Mbytes = data_volume % 1.5
            self.num_total_segments = self.num_full_segments + (1 if self.remaining_Mbytes > 0 else 0)
            # self.snd_nxt = 0
            yield self.env.process(self._send_data(task_id))
        elif type == 'REQUEST':
            print(f"TCP {self.connection_id} at {self.env.now}: Preparing to send data request for task {task_id}")
            yield self.env.process(self.send_segment(task_id=task_id, seq=0, ack=0, flags='REQUEST', data_volume=data_volume))

    def _send_data(self, task_id):
        segments_to_send = min(self.cwnd - (self.snd_nxt - self.snd_una), self.num_total_segments - self.snd_nxt)  # Send as many segments as possible within the congestion window
        print(f"TCP {self.connection_id} at {self.env.now}: allowed to send {segments_to_send} segments") 

        segments_to_send = segments_to_send + self.snd_nxt

        if self.state == 'RECOVERY':
            if len(self.missing_segments) > 0:   
                segments_to_send = max(segments_to_send - self.snd_nxt, 1)
                print(f"TCP {self.connection_id} at {self.env.now}: Recovery - allowed to send {segments_to_send} segments") 
                yield self.env.process(self.retransmit_missing_segments(segments_to_send))
        else:
            while self.snd_nxt < self.num_total_segments:
                print(f"TCP {self.connection_id} at {self.env.now}: Open - sending data") 
                if self.snd_nxt < segments_to_send:
                    if self.snd_nxt < self.num_full_segments:
                        yield self.env.process(self.send_segment(task_id=task_id, seq=self.snd_nxt, flags='DATA', data=1.5))
                    else:
                        yield self.env.process(self.send_segment(task_id=task_id, seq=self.snd_nxt, flags='DATA', data=self.remaining_Mbytes))
                        self.env.process(self._wait_for_acks(task_id, self.num_total_segments))  # Wait for all data segments to be acknowledged and send FIN
                    self.snd_nxt += 1
                else:
                    break

    def receive_segment(self, segment):
        print(f"TCP {self.connection_id} at {self.env.now}: Received segment {segment.flags} with seq {segment.seq} for task {segment.task_id}")
        if segment.flags == 'ACK':
            yield self.env.process(self.handle_ack(segment))
        elif segment.flags == 'FIN':
            self.close()
            # Signal that the data is completely received
            self.dst.receive_segment(segment)
        else:
            # Send an ACK for the received segment
            print(f"TCP {self.connection_id} at {self.env.now}: Received segment {segment.flags} with seq {segment.seq} for task {segment.task_id} - trying to access receive_segment()")
            missing_segments_info = self.dst.receive_segment(segment)
            ack = missing_segments_info.get("ack_number", None)
            missing_segments = missing_segments_info.get("missing_segments", None)
            # print(f"TCP {self.connection_id} at {self.env.now}: Missing segments list to send: {missing_segments}")  
            if ack is not None:
                print(f"TCP {self.connection_id} at {self.env.now}: Received segment {segment.flags} with seq {segment.seq} for task {segment.task_id} - receive_segment() sending ACK={ack}")
                ack_segment = TCPSegment(
                    seq=ack-1, 
                    ack=ack, 
                    flags='ACK', 
                    task_id=segment.task_id, 
                    connection_id=segment.connection_id, 
                    data_volume=segment.data, 
                    missing_segments=missing_segments
                )
                # print(f"TCP {self.connection_id} at {self.env.now}: Sending ack with segment.seq = {ack_segment.seq}, segment.ack = {ack_segment.ack}, and missing semgents = {ack_segment.missing_segments}")
                self.route_segment(ack_segment)                
            else:
                print(f"TCP {self.connection_id} at {self.env.now}: Received segment {segment.flags} with seq {segment.seq} for task {segment.task_id} - Error: ACK could not be generated")