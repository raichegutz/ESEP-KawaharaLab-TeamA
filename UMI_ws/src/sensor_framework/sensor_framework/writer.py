import json
from pathlib import Path
from abc import ABC, abstractmethod

import cv2
import numpy as np


ENCODINGS = {
    'mono8': (np.uint8, 1),
    'mono16': (np.uint16, 1),
    'rgb8': (np.uint8, 3),
    'bgr8': (np.uint8, 3),
    'rgba8': (np.uint8, 4),
    'bgra8': (np.uint8, 4),
}

class Writer(ABC):
    @abstractmethod
    def write(self, records: list) -> None:
        pass


class GelsightWriter(Writer):
    def __init__(self, data_path : Path):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.data_path / 'metadata.json'
        self.images_path = self.data_path / 'images'
        self.images_path.mkdir(parents=True, exist_ok=True)
        self._next_image_indices = {}
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

    def _decode_record(self, record):
        if self._metadata is None:
            raise RuntimeError('image metadata must be written before image data')

        encoding = self._metadata['encoding'].lower()
        if encoding not in ENCODINGS:
            raise ValueError(f'unsupported ROS image encoding: {encoding}')
        dtype, channels = ENCODINGS[encoding]
        height = int(self._metadata['height'])
        width = int(self._metadata['width'])
        step = int(self._metadata['step'])
        item_size = np.dtype(dtype).itemsize
        row_values = step // item_size
        visible_values = width * channels
        raw = bytes(record['data'])

        if step % item_size or row_values < visible_values:
            raise ValueError('image metadata contains an invalid row step')
        if len(raw) != height * step:
            raise ValueError(
                f'image data size is {len(raw)} bytes; expected {height * step}'
            )

        byte_order = '>' if self._metadata.get('is_bigendian', 0) else '<'
        image_dtype = np.dtype(dtype).newbyteorder(byte_order)
        rows = np.frombuffer(raw, dtype=image_dtype).reshape(height, row_values)
        rows = rows[:, :visible_values]
        shape = (height, width) if channels == 1 else (height, width, channels)
        image = rows.reshape(shape)
        conversions = {
            'rgb8': cv2.COLOR_RGB2BGR,
            'rgba8': cv2.COLOR_RGBA2BGRA,
        }
        if encoding in conversions:
            image = cv2.cvtColor(image, conversions[encoding])
        return image

    @staticmethod
    def _safe_camera_name(camera_name):
        safe_name = ''.join(
            character if character.isalnum() or character in '-_' else '_'
            for character in camera_name
        ).strip('_')
        if not safe_name:
            raise ValueError(f'invalid camera name: {camera_name!r}')
        return safe_name

    def _camera_paths(self, camera_name):
        safe_name = self._safe_camera_name(camera_name)
        index_path = self.data_path / f'recording_{safe_name}.jsonl'
        images_path = self.images_path / safe_name
        images_path.mkdir(parents=True, exist_ok=True)

        if safe_name not in self._next_image_indices:
            existing_indices = [
                int(image.stem)
                for image in images_path.glob('*.png')
                if image.stem.isdigit()
            ]
            self._next_image_indices[safe_name] = (
                max(existing_indices, default=-1) + 1
            )
        return safe_name, index_path, images_path

    def write(self, records: dict[str, list]) -> None:
        if not records:
            return

        for camera_name, camera_records in records.items():
            safe_name, index_path, images_path = self._camera_paths(camera_name)
            with index_path.open('a', encoding='utf-8') as recording:
                for record in camera_records:
                    image_index = self._next_image_indices[safe_name]
                    filename = f'{image_index:08d}.png'
                    image = self._decode_record(record)
                    image_path = images_path / filename
                    if not cv2.imwrite(str(image_path), image):
                        raise RuntimeError(f'failed to write image {image_path}')
                    relative_path = image_path.relative_to(self.data_path)
                    index_record = {
                        'timestamp': record['timestamp'],
                        'image': relative_path.as_posix(),
                    }
                    recording.write(json.dumps(index_record) + '\n')
                    self._next_image_indices[safe_name] += 1

class ForceSensorWriter(Writer):
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

    def write(self, records: dict[str, list]) -> None:
        if not records:
            return

        for sensor_name, sensor_records in records.items():
            safe_name = self._safe_sensor_name(sensor_name)
            sensor_path = self.data_path / f'recording_force_{safe_name}.jsonl'
            with sensor_path.open('a', encoding='utf-8') as recording:
                for record in sensor_records:
                    self._validate(record)
                    recording.write(json.dumps(record) + '\n')

    @staticmethod
    def _safe_sensor_name(sensor_name):
        safe_name = ''.join(
            character if character.isalnum() or character in '-_' else '_'
            for character in sensor_name
        ).strip('_')
        if not safe_name:
            raise ValueError(f'invalid force sensor name: {sensor_name!r}')
        return safe_name

    def _validate(self, record: dict):
        required_keys = ['stamp', 'fx', 'fy', 'fz', 'tx', 'ty', 'tz']
        for key in required_keys:
            if key not in record:
                raise ValueError(f'missing key in force record: {key}')

class LedPulseWriter(Writer):
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

    def write(self, records: dict[str, list]) -> None:
        if not records:
            return

        for led_name, led_records in records.items():
            safe_name = self._safe_led_name(led_name)
            led_path = self.data_path / f'recording_led_{safe_name}.jsonl'
            with led_path.open('a', encoding='utf-8') as recording:
                for record in led_records:
                    self._validate(record)
                    recording.write(json.dumps(record) + '\n')

    @staticmethod
    def _safe_led_name(led_name):
        safe_name = ''.join(
            character if character.isalnum() or character in '-_' else '_'
            for character in led_name
        ).strip('_')
        if not safe_name:
            raise ValueError(f'invalid LED name: {led_name!r}')
        return safe_name

    def _validate(self, record: dict):
        required_keys = ['start_stamp', 'end_stamp', 'pulse_id']
        for key in required_keys:
            if key not in record:
                raise ValueError(f'missing key in LED record: {key}')