class Request(object):
    def __init__(self, message, transportInfo, is_update=False, media=None):
        assert transportInfo is not None
        assert message is not None
        self.transport = transportInfo
        self.message = message
        self.media = media
        self.is_update = is_update
