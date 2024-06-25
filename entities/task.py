class Task:
    def __init__(self, env, id, computation, data_volume, category):
        self.env = env
        self.id = id
        self.computation = computation  # Measured in CPU cycles or FLOPs
        self.data_volume = data_volume  # Amount of data in MB
        self.category = category
        self.creation_time = self.env.now
        self.data_request_time = None
        self.data_received_time = None
        self.data_arrival_time = None
        self.start_time = None  # records task processing start time
        self.end_time = None  # records task processing stop time
        self.total_processing_time = None