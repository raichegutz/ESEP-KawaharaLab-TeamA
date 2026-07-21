from glob import glob
import os

from setuptools import find_packages, setup

package_name = "sensor_confidence"

setup(
    name=package_name,
    version="0.1.0",

    packages=find_packages(exclude=["test"]),
    
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/sensor_confidence'],
        ),

        (
            'share/sensor_confidence',
            ['package.xml'],
        ),

        (
            os.path.join("share", package_name, "launch"),
            glob("launch/*.launch.py"),
        ),
        
    ],

    install_requires=[
        "setuptools",
        "numpy",
        "opencv-python",
        "pynput",
    ],

    zip_safe=True,

    maintainer="raich",
    maintainer_email="raicheg@uci.edu",

    description="Multimodal sensor confidence estimation for robotic manipulation.",

    license="Apache-2.0",

    extras_require={
        "test": [
            "pytest",
        ],
    },

    entry_points={
        "console_scripts": [
            "sensor_health_node = sensor_confidence.sensor_health_node:main",
        ],
    },
)