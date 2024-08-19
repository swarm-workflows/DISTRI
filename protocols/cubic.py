from protocols.helpers.tcp_cc import CongestionControl
import math
import time

class Cubic(CongestionControl):
    BICTCP_BETA_SCALE = 1024
    BICTCP_HZ = 10
    BETA = 717  # 717 / 1024
    C = 0.4
    CUBE_SCALE = 410
    BETA_SCALE = 819
    CUBE_FACTOR = 1 << (3 * BICTCP_HZ + 10)
    FAST_CONVERGENCE = 1

    def __init__(self, connection):
        super().__init__(connection)
        self.epoch_start = None
        self.last_max_cwnd = 0
        self.loss_cwnd = 0
        self.last_cwnd = 0
        self.last_time = 0
        self.bic_origin_point = 0
        self.bic_K = 0
        self.delay_min = 0
        self.ack_cnt = 0
        self.tcp_cwnd = 0
        self.cnt = 0
        self.t_last_loss = 0

    def cubic_root(self, a):
        """Approximate cubic root using Newton-Raphson method."""
        if a <= 0:
            return 0
        x = a >> 6
        if x == 0:
            return a
        b = (self.BICTCP_HZ * 84) >> 8
        shift = a >> (b * 3)
        x = ((shift + 10) << b) >> 6
        x = (2 * x + (a // (x * x))) // 3
        return x

    def update_cubic(self, cwnd, acked):
        self.ack_cnt += acked
        if self.last_cwnd == cwnd and (time.time() - self.last_time) <= 1 / 32:
            return
        if self.epoch_start and time.time() == self.last_time:
            return

        self.last_cwnd = cwnd
        self.last_time = time.time()

        if self.epoch_start is None:
            self.epoch_start = time.time()
            self.ack_cnt = acked
            self.tcp_cwnd = cwnd

            if self.last_max_cwnd <= cwnd:
                self.bic_K = 0
                self.bic_origin_point = cwnd
            else:
                self.bic_K = self.cubic_root(int(self.CUBE_FACTOR * (self.last_max_cwnd - cwnd)))
                self.bic_origin_point = self.last_max_cwnd

        t = time.time() - self.epoch_start
        offs = (t - self.bic_K) ** 3 if t >= self.bic_K else (self.bic_K - t) ** 3

        delta = (self.CUBE_SCALE * int(offs)) >> (10 + 3 * self.BICTCP_HZ)
        bic_target = self.bic_origin_point - delta if t < self.bic_K else self.bic_origin_point + delta

        if bic_target > cwnd:
            self.cnt = cwnd // (bic_target - cwnd)
        else:
            self.cnt = 100 * cwnd

        if self.last_max_cwnd == 0 and self.cnt > 20:
            self.cnt = 20

        scale = self.BETA_SCALE
        delta = (int(cwnd) * scale) >> 3
        while self.ack_cnt > delta:
            self.ack_cnt -= delta
            self.tcp_cwnd += 1

        if self.tcp_cwnd > cwnd:
            delta = self.tcp_cwnd - cwnd
            max_cnt = cwnd // delta
            if self.cnt > max_cnt:
                self.cnt = max_cnt

        self.cnt = max(self.cnt, 2)

    def on_ack(self):
        if self.connection.cwnd < self.connection.ssthresh:
            self.connection.update_cwnd(self.connection.cwnd + 1)
            print(f"Cubic CCA: Slow start phase, cwnd increased to {self.connection.cwnd}")
        else:
            self.update_cubic(self.connection.cwnd, 1)
            self.connection.update_cwnd(self.connection.cwnd + 1 / self.cnt)
            print(f"Cubic CCA: Congestion avoidance phase, cwnd updated to {self.connection.cwnd}")

    def on_loss(self, is_timeout=False):
        if is_timeout:
            print("Cubic CCA: Timeout detected")
            self.last_max_cwnd = self.connection.cwnd
            self.connection.ssthresh = max(self.connection.cwnd // 2, 1)
            self.connection.update_cwnd(1)
            print(f"Cubic CCA: ssthresh set to {self.connection.ssthresh}, cwnd reset to {self.connection.cwnd} due to timeout")
            self.epoch_start = None
        else:
            print("Cubic CCA: Packet loss detected")
            self.last_max_cwnd = self.connection.cwnd
            self.connection.ssthresh = max(self.connection.cwnd // 2, 1)
            self.connection.update_cwnd(self.connection.ssthresh)
            print(f"Cubic CCA: ssthresh set to {self.connection.ssthresh}, cwnd reset to {self.connection.cwnd}")
            self.epoch_start = None

    def on_recovery(self):
        self.connection.update_cwnd(self.connection.cwnd + 1)
        print(f"Cubic CCA: Fast recovery phase, cwnd updated to {self.connection.cwnd}")
