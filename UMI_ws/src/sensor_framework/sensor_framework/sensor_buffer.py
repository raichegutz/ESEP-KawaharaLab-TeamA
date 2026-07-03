from collections import defaultdict
from threading import Lock

from .writer import Writer


class SensorDataBuffer:
    def __init__(self):
        self._data = list()
        self._lock = Lock()

    def append(self, topic_name: str, data) -> None:
        with self._lock:
            self._data.append(data)

    def pop_all(self, writer: Writer) -> None:
        with self._lock:
            writer.write(self._data)
            self._data.clear()