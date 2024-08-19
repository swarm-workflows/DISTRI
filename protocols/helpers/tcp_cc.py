class CongestionControl:
    def __init__(self, connection):
        self.connection = connection

    def on_ack(self, ack):
        pass

    def on_loss(self):
        pass