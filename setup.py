from setuptools import setup, find_packages

setup(
    name='tf_policies_generator',
    version='0.1.0',
    description='Generate policies from terraform plan',
    author='Crowdsec',
    url="https://github.com/crowdsecurity/tf-policies-generator",
    python_requires='>=3.6',
    packages=["tf_policies_generator"],
    entry_points={
        'console_scripts': [
            'tf_policies_generator = tf_policies_generator.main:main',
        ],
    },
)