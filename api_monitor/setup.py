from setuptools import setup, find_packages

setup(
    name="api_monitor",
    version="0.1.0",
    description="API Monitoring System",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.0',
        'apscheduler>=3.7.0',
        'python-dateutil>=2.8.1',
        'typing-extensions>=3.7.4'
    ],
    entry_points={
        'console_scripts': [
            'api_monitor=api_monitor.__main__:main',
        ],
    },
)
