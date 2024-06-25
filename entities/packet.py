class Packet:
    def __init__(self, source, destination, packet_type, packet_size=1, task_id=None, data_volume=0):
        self.source = source
        self.destination = destination
        self.packet_type = packet_type
        self.packet_size = packet_size  # Default size is 1 if not specified
        self.task_id = task_id          # Default is none if not specified
        self.data_volume = data_volume  # Default volume is 0 if not specified

    def __repr__(self):
        return (f"Packet(type={self.packet_type}, size={self.packet_size}, task_id={self.task_id}, "
                f"data_volume={self.data_volume}, from={self.source}, to={self.destination})")