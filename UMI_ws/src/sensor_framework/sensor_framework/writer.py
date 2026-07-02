import json

class JsonlWriter:
    def __init__(self, path):
        self.path = path

    def write_many(self, records):
        if not records:
            return

        with open(self.path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")