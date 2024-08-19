from protocols.helpers.tcp_cc import CongestionControl

class Reno(CongestionControl):
    def __init__(self, connection):
        super().__init__(connection)

    def on_ack(self):
        # Implement Reno-specific ACK handling
        if self.connection.cwnd < self.connection.ssthresh:
            self.connection.update_cwnd(self.connection.cwnd + 1)
            print(f"Reno CCA: Slow start phase, cwnd increased to {self.connection.cwnd}")
        else:
            # Congestion avoidance: cwnd += 1 / cwnd for each ack
            increment = 1 / self.connection.cwnd
            self.connection.update_cwnd(self.connection.cwnd + increment)
            print(f"Reno CCA: Congestion avoidance phase, cwnd increased to {self.connection.cwnd}")

    def on_loss(self, is_timeout=False):
        if is_timeout:
            # Timeout occurred
            print("Reno CCA: Timeout detected")
            self.connection.ssthresh = max(self.connection.cwnd // 2, 2)
            self.connection.update_cwnd(1)
            print(f"Reno CCA: ssthresh set to {self.connection.ssthresh}, cwnd reset to {self.connection.cwnd} due to timeout")
        else:
            # Packet loss detected
            print("Reno CCA: Packet loss detected")
            self.connection.ssthresh = max(self.connection.cwnd // 2, 2)
            self.connection.update_cwnd(self.connection.ssthresh)
            print(f"Reno CCA: ssthresh set to {self.connection.ssthresh}, cwnd reset to {self.connection.cwnd}")

    def on_recovery(self):
        # Increment cwnd by 1 for each duplicate ACK in fast recovery
        self.connection.update_cwnd(self.connection.cwnd + 1)
        print(f"Reno CCA: Fast recovery phase, cwnd increased to {self.connection.cwnd}")
