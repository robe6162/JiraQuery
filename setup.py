import pprint

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'name': 'defect_metrics',
    'description': 'Defect Query and Metric Analysis',
    'version': '0.0.1',
    'author': 'Tech Mahindra',
    'install_requires': ['requests', 'pyyaml', 'prettytable'],
}

print("CONFIG:\n{0}".format(pprint.pformat(config)))
setup(**config)
