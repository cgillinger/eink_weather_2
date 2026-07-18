# Stub för Waveshare EPD (används inte i web version)
# IS_STUB låter main_daemon/main.py upptäcka att den RIKTIGA drivrutinen
# saknas och vägra starta - annars kör daemonen tyst utan att skärmen
# någonsin uppdateras (stubben skuggar vendor-drivrutinen i sys.path)
IS_STUB = True


class EPD:
    def __init__(self):
        pass
    def init(self):
        pass
    def Clear(self):
        pass
    def display(self, image):
        pass
    def sleep(self):
        pass
    def getbuffer(self, image):
        return image
