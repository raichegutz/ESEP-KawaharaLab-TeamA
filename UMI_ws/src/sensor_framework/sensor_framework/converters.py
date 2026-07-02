def stamp_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def image_msg_to_record(msg):
    return {
        "timestamp": stamp_to_ns(msg.header.stamp),
        "data": list(msg.data),
    }


def image_msg_to_metadata(msg):
    return {
        "height": msg.height,
        "width": msg.width,
        "encoding": msg.encoding,
        "is_bigendian": msg.is_bigendian,
        "step": msg.step,
    }


def array_msg_to_record(msg, timestamp_ns):
    return {
        "timestamp": timestamp_ns,
        "values": list(msg.data),
    }
