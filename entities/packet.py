class Packet:
    def __init__(self, source, destination, packet_type, packet_size=1, segment_seq=None, segment_flag=None, segment_ack=None, task_id=None, data=0, data_volume=0, connection_id=None, connection = None, missing_segments=None):
        self.source = source
        self.destination = destination
        self.packet_type = packet_type
        self.packet_size = packet_size  # Default size is 1 if not specified
        self.segment_seq = segment_seq  # Default is none if not specified
        self.segment_flag = segment_flag  # Default is none if not specified
        self.segment_ack = segment_ack  # Default is none if not specified
        self.task_id = task_id          # Default is none if not specified
        self.data = data  # Default volume is 0 if not specified
        self.data_volume = data_volume  # Default volume is 0 if not specified
        self.connection_id = connection_id  # Unique connection ID
        self.connection = connection
        self.missing_segments = missing_segments if missing_segments is not None else []  # List of missing segments for selective repeat

    def __repr__(self):
        return (f"Packet(type={self.packet_type}, size={self.packet_size}, segment_seq={self.segment_seq}, segment_flag={self.segment_flag}, segment_ack={self.segment_ack}, task_id={self.task_id}, "
                f"data={self.data}, data_volume={self.data_volume}, from={self.source}, to={self.destination}, with connection_id={self.connection_id}, and missing segments={len(self.missing_segments)})")