class Request(object):
    def __init__(self, message, media, transportInfo, is_update=False):
        assert transportInfo is not None
        assert message is not None
        self.transport = transportInfo
        self.message = message
        self.media = media
        self.is_update = is_update
