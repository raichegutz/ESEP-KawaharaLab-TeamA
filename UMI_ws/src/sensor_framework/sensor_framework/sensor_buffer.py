from collections import defaultdict
from threading import Lock


class SensorDataBuffer:
    def __init__(self):
        self._data: dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def append(self, topic_name: str, data) -> None:
        with self._lock:
            self._data[topic_name].append(data)

    def pop_all(self, writer) -> None:
        with self._lock:
            records = self._data
            writer.write(records)
            self._data.clear()