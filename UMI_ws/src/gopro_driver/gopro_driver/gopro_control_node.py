import asyncio
from concurrent.futures import TimeoutError
import json
import threading
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger


class GoProSdkController:
    def __init__(self, node: Node):
        self.node = node
        self.connection = node.get_parameter('connection').value
        self.identifier = node.get_parameter('identifier').value
        self.command_transport = node.get_parameter('command_transport').value
        self.service_timeout_sec = float(node.get_parameter('service_timeout_sec').value)

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._gopro = None

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def close(self):
        try:
            if self._gopro is not None:
                self._run(self._gopro.close())
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=2.0)

    def connect(self):
        return self._run(self._connect())

    def start_recording(self):
        return self._run(self._set_shutter(True))

    def stop_recording(self):
        return self._run(self._set_shutter(False))

    def get_state(self):
        return self._run(self._get_state())

    def _run(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=self.service_timeout_sec)
        except TimeoutError as exc:
            future.cancel()
            raise RuntimeError(
                f'GoPro SDK command timed out after {self.service_timeout_sec:.1f}s'
            ) from exc

    async def _connect(self):
        if self._gopro is not None:
            return 'already connected'

        try:
            from open_gopro import WiredGoPro, WirelessGoPro
        except ImportError as exc:
            raise RuntimeError(
                'OpenGoPro SDK is not installed. Install it in the ROS2 Python '
                'environment with: python3 -m pip install open-gopro'
            ) from exc

        kwargs: dict[str, Any] = {}
        if self.identifier:
            kwargs['identifier'] = self.identifier

        if self.connection == 'wired':
            self._gopro = WiredGoPro(**kwargs)
        elif self.connection == 'wireless':
            self._gopro = WirelessGoPro(**kwargs)
        else:
            raise ValueError("connection must be 'wired' or 'wireless'")

        await self._gopro.open()
        return f'connected via {self.connection}'

    async def _ensure_connected(self):
        if self._gopro is None:
            await self._connect()

    async def _set_shutter(self, enabled: bool):
        await self._ensure_connected()

        try:
            from open_gopro import Params
        except ImportError as exc:
            raise RuntimeError('OpenGoPro SDK import failed after startup.') from exc

        shutter = Params.Toggle.ENABLE if enabled else Params.Toggle.DISABLE
        transport = self.command_transport

        if transport == 'auto':
            transport = 'http' if self.connection == 'wired' else 'ble'

        if transport == 'http':
            response = await self._gopro.http_command.set_shutter(shutter=shutter)
        elif transport == 'ble':
            response = await self._gopro.ble_command.set_shutter(shutter=shutter)
        else:
            raise ValueError("command_transport must be 'auto', 'http', or 'ble'")

        if hasattr(response, 'ok') and not response.ok:
            raise RuntimeError(str(response))

        return str(response)

    async def _get_state(self):
        await self._ensure_connected()
        response = await self._gopro.http_command.get_camera_state()
        return str(response)


class GoProControlNode(Node):
    def __init__(self):
        super().__init__('gopro_control_node')

        self.declare_parameter('connection', 'wired')
        self.declare_parameter('identifier', '')
        self.declare_parameter('command_transport', 'auto')
        self.declare_parameter('connect_on_startup', True)
        self.declare_parameter('service_timeout_sec', 15.0)

        self.controller = GoProSdkController(self)
        self.event_pub = self.create_publisher(String, '/gopro/record_event', 10)

        self.create_service(Trigger, '/gopro/start_record', self.handle_start_record)
        self.create_service(Trigger, '/gopro/stop_record', self.handle_stop_record)
        self.create_service(Trigger, '/gopro/get_state', self.handle_get_state)

        if bool(self.get_parameter('connect_on_startup').value):
            try:
                message = self.controller.connect()
                self.get_logger().info(f'GoPro SDK {message}')
            except Exception as exc:
                self.get_logger().warn(
                    'GoPro SDK did not connect on startup: '
                    f'{exc}. Services will retry on first call.'
                )

        self.get_logger().info(
            'GoPro control services ready: /gopro/start_record, '
            '/gopro/stop_record, /gopro/get_state'
        )

    def handle_start_record(self, request, response):
        return self._handle_record_command('start_record', self.controller.start_recording, response)

    def handle_stop_record(self, request, response):
        return self._handle_record_command('stop_record', self.controller.stop_recording, response)

    def handle_get_state(self, request, response):
        try:
            response.message = self.controller.get_state()
            response.success = True
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_record_command(self, event_name, command, response):
        ros_time_ns = self.get_clock().now().nanoseconds
        try:
            sdk_response = command()
            self._publish_event(event_name, ros_time_ns, True, sdk_response)
            response.success = True
            response.message = sdk_response
        except Exception as exc:
            self._publish_event(event_name, ros_time_ns, False, str(exc))
            response.success = False
            response.message = str(exc)
        return response

    def _publish_event(self, event_name: str, ros_time_ns: int, success: bool, detail: str):
        msg = String()
        msg.data = json.dumps({
            'event': event_name,
            'ros_time_ns': ros_time_ns,
            'success': success,
            'detail': detail,
        })
        self.event_pub.publish(msg)

    def destroy_node(self):
        if hasattr(self, 'controller'):
            self.controller.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = GoProControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
