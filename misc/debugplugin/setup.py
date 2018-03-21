from setuptools import setup

# Minimal setup.py to demonstrate loading an external plugin

setup(
    name='kitovu-debug',
    py_modules=['kitovu_debug'],
    entry_points={
        'kitovu.sync.plugin': [
            'debug = kitovu_debug:DebugPlugin',
        ]
    }
)
