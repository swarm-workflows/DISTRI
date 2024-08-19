from protocols.helpers.tcp_cc import CongestionControl
import time

class HTCP(CongestionControl):
    ALPHA_BASE = 1 << 7  # 1.0 with shift << 7
    BETA_MIN = 1 << 6  # 0.5 with shift << 7
    BETA_MAX = 102  # 0.8 with shift << 7

    def __init__(self, connection):
        super().__init__(connection)
        self.alpha = self.ALPHA_BASE
        self.beta = self.BETA_MIN
        self.modeswitch = False
        self.pkts_acked = 1
        self.packetcount = 0
        self.minRTT = 0
        self.maxRTT = 0
        self.last_cong = time.time()
        self.undo_last_cong = 0
        self.undo_maxRTT = 0
        self.undo_old_maxB = 0
        self.minB = 0
        self.maxB = 0
        self.old_maxB = 0
        self.Bi = 0
        self.lasttime = 0

    def htcp_cong_time(self):
        return time.time() - self.last_cong

    def htcp_ccount(self):
        return self.htcp_cong_time() / (self.minRTT if self.minRTT != 0 else 1)

    def htcp_reset(self):
        self.undo_last_cong = self.last_cong
        self.undo_maxRTT = self.maxRTT
        self.undo_old_maxB = self.old_maxB
        self.last_cong = time.time()

    def measure_rtt(self):
        srtt = self.connection.srtt
        if srtt:
            if self.minRTT > srtt or self.minRTT == 0:
                self.minRTT = srtt
            if self.connection.state == "OPEN":
                if self.maxRTT < self.minRTT:
                    self.maxRTT = self.minRTT
                if self.maxRTT < srtt <= self.maxRTT + 0.02:
                    self.maxRTT = srtt
            print(f"HTCP: RTT measured - minRTT={self.minRTT}, maxRTT={self.maxRTT}")

    def measure_achieved_throughput(self):
        throughput_log = self.connection.throughput_log
        if not throughput_log.empty:
            latest_throughput = throughput_log.iloc[-1]['throughput']
            now = self.connection.env.now

            if self.connection.state in ("OPEN", "DISORDER"):
                self.packetcount += latest_throughput
                if self.packetcount >= self.connection.cwnd - (self.alpha / 128 if self.alpha / 128 != 0 else 1) and now - self.lasttime >= self.minRTT and self.minRTT > 0:
                    cur_Bi = self.packetcount / (now - self.lasttime)
                    if self.htcp_ccount() <= 3:
                        self.minB = self.maxB = self.Bi = cur_Bi
                    else:
                        self.Bi = (3 * self.Bi + cur_Bi) / 4
                        if self.Bi > self.maxB:
                            self.maxB = self.Bi
                        if self.minB > self.maxB:
                            self.minB = self.maxB
                    self.packetcount = 0
                    self.lasttime = now
            print(f"HTCP: Throughput measured - Bi={self.Bi}, minB={self.minB}, maxB={self.maxB}")

    def htcp_beta_update(self):
        if self.modeswitch and self.minRTT > 0.01 and self.maxRTT:
            self.beta = (self.minRTT * 128) / self.maxRTT
            if self.beta < self.BETA_MIN:
                self.beta = self.BETA_MIN
            elif self.beta > self.BETA_MAX:
                self.beta = self.BETA_MAX
        else:
            self.beta = self.BETA_MIN
            self.modeswitch = True
        print(f"HTCP: Beta updated - beta={self.beta}")

    def htcp_alpha_update(self):
        factor = 1
        diff = self.htcp_cong_time()
        if diff > 1:
            diff -= 1
            factor = 1 + (10 * diff + ((diff / 2) * (diff / 2) / 1)) / 1
        if self.minRTT:
            scale = (1 * 8) / (10 * self.minRTT)
            scale = min(max(scale, 4), 80)
            factor = (factor * 8) / scale
            if factor == 0:
                factor = 1
        self.alpha = 2 * factor * (128 - self.beta)
        if self.alpha == 0:
            self.alpha = self.ALPHA_BASE
        print(f"HTCP: Alpha updated - alpha={self.alpha}")

    def on_ack(self):
        self.measure_rtt()
        self.measure_achieved_throughput()
        if self.connection.cwnd < self.connection.ssthresh:
            self.connection.update_cwnd(self.connection.cwnd + 1)
            print(f"H-TCP: Slow start phase, cwnd increased to {self.connection.cwnd}")
        else:
            self.htcp_alpha_update()
            increment = (self.alpha / 128) / self.connection.cwnd
            self.connection.update_cwnd(self.connection.cwnd + increment)
            print(f"H-TCP: Congestion avoidance phase, cwnd increased to {self.connection.cwnd}, alpha={self.alpha}")

    def on_loss(self, is_timeout=False):
        self.measure_rtt()
        if is_timeout:
            print("H-TCP: Timeout detected")
            self.connection.ssthresh = max(self.connection.cwnd // 2, 2)
            self.connection.update_cwnd(1)
            print(f"H-TCP: ssthresh set to {self.connection.ssthresh}, cwnd reset to {self.connection.cwnd} due to timeout")
        else:
            print("H-TCP: Packet loss detected")
            self.connection.ssthresh = max(self.connection.cwnd // 2, 2)
            self.connection.update_cwnd(self.connection.ssthresh)
            self.htcp_reset()
            print(f"H-TCP: ssthresh set to {self.connection.ssthresh}, cwnd reset to {self.connection.cwnd}")

    def on_recovery(self):
        self.connection.update_cwnd(self.connection.cwnd + 1)
        print(f"H-TCP: Fast recovery phase, cwnd increased to {self.connection.cwnd}")
