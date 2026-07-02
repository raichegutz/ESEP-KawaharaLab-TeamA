import json
from pathlib import Path

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


class JsonlWriter:
    def __init__(self, path, metadata_path=None):
        self.path = Path(path)
        self.metadata_path = (
            Path(metadata_path) if metadata_path else self.path.with_name('metadata.json')
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.images_path = self.path.parent / 'images'
        self.images_path.mkdir(parents=True, exist_ok=True)
        existing_indices = [
            int(image.stem)
            for image in self.images_path.glob('*.png')
            if image.stem.isdigit()
        ]
        self._next_image_index = max(existing_indices, default=-1) + 1
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

    def write(self, records: dict[str, list]) -> None:
        if not records:
            return

        with self.path.open('a', encoding='utf-8') as recording:
            for topic_records in records.values():
                for record in topic_records:
                    filename = f'{self._next_image_index:08d}.png'
                    relative_path = Path('images') / filename
                    image = self._decode_record(record)
                    if not cv2.imwrite(str(self.path.parent / relative_path), image):
                        raise RuntimeError(f'failed to write image {relative_path}')
                    index_record = {
                        'timestamp': record['timestamp'],
                        'image': relative_path.as_posix(),
                    }
                    recording.write(json.dumps(index_record) + '\n')
                    self._next_image_index += 1
