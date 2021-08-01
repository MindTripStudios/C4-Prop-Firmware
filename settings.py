import ujson

class Settings:
    def __init__(self):
        self.file = "settings.json"
        self.json = {}
        self.load_settings()
        # self.save_settings()
        
    def load_settings(self):
        file = open(self.file)
        self.json = ujson.loads(file.read())
        file.close()
        
    def save_settings(self):
        file = open(self.file, "w")
        file.write(ujson.dumps(self.json))
        file.close()
        
        
        