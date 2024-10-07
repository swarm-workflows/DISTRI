class TCPSegment:
    def __init__(self, seq=None, ack=None, flags=None, job_id=None, connection_id=None, data_volume=0, data=0, missing_segments=None):
        self.seq = seq
        self.ack = ack
        self.flags = flags  # SYN, ACK, FIN, DATA, REQUEST (custom for data requests)
        self.job_id = job_id
        self.connection_id = connection_id
        self.data_volume = data_volume
        self.data = data
        self.send_time = None  # Time when the segment is sent
        self.missing_segments = missing_segments if missing_segments is not None else []  # List of missing segments for selective repeat