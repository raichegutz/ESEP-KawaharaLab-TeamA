from glob import glob
import os

from setuptools import find_packages, setup


package_name = 'gopro_driver'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='umi_team',
    maintainer_email='todo@example.com',
    description='GoPro HDMI capture driver for the UMI sensor framework.',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gopro_node = gopro_driver.gopro_node:main',
            'gopro_control_node = gopro_driver.gopro_control_node:main',
        ],
    },
)
