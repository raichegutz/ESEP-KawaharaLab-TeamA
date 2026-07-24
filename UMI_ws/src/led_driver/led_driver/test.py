#!/usr/bin/env python3

import time
from gpiozero import LED

GPIO_PIN = 4

led = LED(GPIO_PIN)

print(f"Blinking GPIO {GPIO_PIN}... Press Ctrl+C to stop.")

try:
    while True:
        print("ON")
        led.on()
        time.sleep(0.5)

        print("OFF")
        led.off()
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    led.off()
