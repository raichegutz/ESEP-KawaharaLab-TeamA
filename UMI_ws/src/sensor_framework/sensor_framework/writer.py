import json
from pathlib import Path


class JsonlWriter:
    def __init__(self, path, metadata_path=None):
        self.path = Path(path)
        self.metadata_path = (
            Path(metadata_path) if metadata_path else self.path.with_name('metadata.json')
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._metadata = None
        if self.metadata_path.exists():
            with self.metadata_path.open(encoding='utf-8') as metadata_file:
                self._metadata = json.load(metadata_file)

    def write_metadata(self, metadata):
        if self._metadata is not None:
            if metadata != self._metadata:
                raise ValueError(
                    'image metadata changed during recording: '
                    f'expected {self._metadata}, got {metadata}'
                )
            return

        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open('w', encoding='utf-8') as metadata_file:
            json.dump(metadata, metadata_file, indent=2)
            metadata_file.write('\n')
        self._metadata = metadata.copy()

    def write(self, records: dict[str, list]) -> None:
        if not records:
            return

        with self.path.open('a', encoding='utf-8') as recording:
            for topic_records in records.values():
                for record in topic_records:
                    recording.write(json.dumps(record) + '\n')
