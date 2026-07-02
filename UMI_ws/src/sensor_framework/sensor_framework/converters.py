def stamp_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def image_msg_to_record(msg):
    return {
        "timestamp": stamp_to_ns(msg.header.stamp),
        "height": msg.height,
        "width": msg.width,
        "encoding": msg.encoding,
        "is_bigendian": msg.is_bigendian,
        "step": msg.step,
        "data_size": len(msg.data),
        "data": list(msg.data),
    }


def array_msg_to_record(msg, timestamp_ns):
    return {
        "timestamp": timestamp_ns,
        "values": list(msg.data),
    }
