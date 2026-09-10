from setuptools import find_packages, setup

package_name = 'waypoint_tools'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='cowltnr',
    maintainer_email='sue030124@naver.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        'marker = waypoint_tools.marker:main',
        'point_follower = waypoint_tools.point_follower:main',
        'pure_pursuit_follower = waypoint_tools.pure_pursuit_follower:main',
        'lookahead_follower = waypoint_tools.lookahead_follower:main',
        'intent_decision = waypoint_tools.intent_decision:main',
        ],
    },
)
