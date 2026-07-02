import argparse
import json
import tkinter as tk
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk


ENCODINGS = {
    'mono8': (np.uint8, 1),
    'mono16': (np.uint16, 1),
    'rgb8': (np.uint8, 3),
    'bgr8': (np.uint8, 3),
    'rgba8': (np.uint8, 4),
    'bgra8': (np.uint8, 4),
}


def read_image_record(path: Path, image_index: int) -> dict:
    if image_index < 0:
        raise ValueError('image index must be non-negative')

    current_index = 0
    with path.open(encoding='utf-8') as recording:
        for line_number, line in enumerate(recording, start=1):
            if not line.strip():
                continue

            batch = json.loads(line)
            if isinstance(batch, dict):
                batch = [batch]
            if not isinstance(batch, list):
                raise ValueError(f'line {line_number} is not an image-record list')

            next_index = current_index + len(batch)
            if image_index < next_index:
                record = batch[image_index - current_index]
                if not isinstance(record, dict) or 'data' not in record:
                    raise ValueError(f'image {image_index} is not a valid image record')
                metadata_path = path.with_name('metadata.json')
                if metadata_path.exists():
                    with metadata_path.open(encoding='utf-8') as metadata_file:
                        return {**json.load(metadata_file), **record}
                return record
            current_index = next_index

    raise IndexError(
        f'image index {image_index} is out of range; file contains '
        f'{current_index} images'
    )


class RecordingReader:
    """Navigate image records while retaining only one JSONL batch."""

    def __init__(self, path: Path, image_index: int = 0):
        if image_index < 0:
            raise ValueError('image index must be non-negative')
        self._file = path.open(encoding='utf-8')
        metadata_path = path.with_name('metadata.json')
        if metadata_path.exists():
            with metadata_path.open(encoding='utf-8') as metadata_file:
                self._metadata = json.load(metadata_file)
        else:
            self._metadata = {}
        self._offsets = []
        self._batch = []
        self._batch_index = -1
        self._record_index = 0
        self._next_offset = 0
        self.image_index = 0
        self._seek(image_index)

    @property
    def current(self) -> dict:
        return {**self._metadata, **self._batch[self._record_index]}

    def _read_batch(self, offset):
        self._file.seek(offset)
        while True:
            actual_offset = self._file.tell()
            line = self._file.readline()
            if not line:
                return None
            if line.strip():
                break
        batch = json.loads(line)
        if isinstance(batch, dict):
            batch = [batch]
        if not isinstance(batch, list) or not batch:
            raise ValueError('recording contains an invalid or empty image batch')
        return batch, actual_offset, self._file.tell()

    def _seek(self, target_index):
        offset = 0
        first_index = 0
        while True:
            result = self._read_batch(offset)
            if result is None:
                raise IndexError(
                    f'image index {target_index} is out of range; file contains '
                    f'{first_index} images'
                )
            batch, actual_offset, next_offset = result
            self._offsets.append(actual_offset)
            if target_index < first_index + len(batch):
                self._batch = batch
                self._batch_index = len(self._offsets) - 1
                self._record_index = target_index - first_index
                self._next_offset = next_offset
                self.image_index = target_index
                return
            first_index += len(batch)
            offset = next_offset

    def next(self):
        if self._record_index + 1 < len(self._batch):
            self._record_index += 1
        else:
            result = self._read_batch(self._next_offset)
            if result is None:
                return False
            self._batch, actual_offset, self._next_offset = result
            self._batch_index += 1
            if self._batch_index == len(self._offsets):
                self._offsets.append(actual_offset)
            self._record_index = 0
        self.image_index += 1
        return True

    def previous(self):
        if self.image_index == 0:
            return False
        if self._record_index > 0:
            self._record_index -= 1
        else:
            self._batch_index -= 1
            result = self._read_batch(self._offsets[self._batch_index])
            self._batch, _, self._next_offset = result
            self._record_index = len(self._batch) - 1
        self.image_index -= 1
        return True

    def close(self):
        self._file.close()


def decode_image(record: dict) -> np.ndarray:
    encoding = record['encoding'].lower()
    if encoding not in ENCODINGS:
        raise ValueError(f'unsupported ROS image encoding: {encoding}')

    dtype, channels = ENCODINGS[encoding]
    height = int(record['height'])
    width = int(record['width'])
    step = int(record['step'])
    item_size = np.dtype(dtype).itemsize
    row_values = step // item_size
    visible_values = width * channels

    if row_values < visible_values or step % item_size:
        raise ValueError('record has an invalid row step')

    raw = bytes(record['data'])
    expected_size = height * step
    if len(raw) < expected_size:
        raise ValueError(
            f'image data is truncated: expected {expected_size} bytes, got {len(raw)}'
        )

    byte_order = '>' if record.get('is_bigendian', 0) else '<'
    image_dtype = np.dtype(dtype).newbyteorder(byte_order)
    rows = np.frombuffer(raw[:expected_size], dtype=image_dtype)
    rows = rows.reshape(height, row_values)[:, :visible_values]
    if channels == 1:
        image = rows.reshape(height, width)
    else:
        image = rows.reshape(height, width, channels)

    conversions = {
        'rgb8': cv2.COLOR_RGB2BGR,
        'rgba8': cv2.COLOR_RGBA2BGRA,
    }
    if encoding in conversions:
        image = cv2.cvtColor(image, conversions[encoding])
    return image


def parse_args():
    parser = argparse.ArgumentParser(
        description='Display a raw image stored in a sensor_framework JSONL recording.'
    )
    parser.add_argument(
        'recording',
        nargs='?',
        type=Path,
        default=Path('data/recording.jsonl'),
        help='recording path (default: data/recording.jsonl)',
    )
    parser.add_argument(
        '--index',
        type=int,
        default=0,
        help='zero-based image index across all JSONL batches (default: 0)',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='write the image to this path instead of opening a window',
    )
    return parser.parse_args()


def to_display_array(image, encoding):
    if encoding in ('bgr8', 'rgb8'):
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    if encoding in ('bgra8', 'rgba8'):
        return cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
    if encoding == 'mono16':
        return cv2.convertScaleAbs(image, alpha=255.0 / 65535.0)
    return image


def display_slideshow(reader):
    root = tk.Tk()
    root.title('Recorded images')
    image_label = tk.Label(root)
    image_label.pack()
    status_label = tk.Label(root)
    status_label.pack(pady=4)
    controls = tk.Frame(root)
    controls.pack(pady=(0, 8))

    def refresh():
        record = reader.current
        image = decode_image(record)
        image = to_display_array(image, record['encoding'].lower())
        photo = ImageTk.PhotoImage(Image.fromarray(image))
        image_label.configure(image=photo)
        image_label.image = photo
        status_label.configure(
            text=f"Image {reader.image_index} | {record['width']}x{record['height']} "
            f"| {record['encoding']}"
        )

    def show_next(_event=None):
        if reader.next():
            refresh()

    def show_previous(_event=None):
        if reader.previous():
            refresh()

    tk.Button(controls, text='Previous', command=show_previous).pack(
        side=tk.LEFT, padx=4
    )
    tk.Button(controls, text='Next', command=show_next).pack(
        side=tk.LEFT, padx=4
    )
    root.bind('<Left>', show_previous)
    root.bind('<Right>', show_next)
    root.bind('<Escape>', lambda _event: root.destroy())
    root.bind('q', lambda _event: root.destroy())
    root.protocol('WM_DELETE_WINDOW', root.destroy)
    refresh()
    root.mainloop()


def main():
    args = parse_args()
    reader = RecordingReader(args.recording, args.index)
    try:
        if args.output:
            image = decode_image(reader.current)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(args.output), image):
                raise RuntimeError(f'failed to write image to {args.output}')
            print(f'Wrote image {args.index} to {args.output}')
            return
        print('Use arrow keys or buttons. Press Q or Escape to close.')
        display_slideshow(reader)
    finally:
        reader.close()


if __name__ == '__main__':
    main()
