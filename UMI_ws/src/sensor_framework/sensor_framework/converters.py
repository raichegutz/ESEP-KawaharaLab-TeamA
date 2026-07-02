def stamp_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def image_msg_to_record(msg):
    return {
        "timestamp_ns": stamp_to_ns(msg.header.stamp),
        "height": msg.height,
        "width": msg.width,
        "encoding": msg.encoding,
        # For real image recording, avoid dumping raw bytes to JSON.
        # Use HDF5, NPZ, image files, or rosbag instead.
        "data_size": len(msg.data),
    }


def array_msg_to_record(msg, timestamp_ns):
    return {
        "timestamp_ns": timestamp_ns,
        "values": list(msg.data),
    }