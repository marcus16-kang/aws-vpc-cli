from setuptools import setup, find_packages

requires = [
    'ansicon>=1.89.0',
    'aws-cloudformation-visualizer>=0.0.3',
    'blessed>=1.20.0',
    'boto3>=1.26.81',
    'botocore>=1.29.81',
    'inquirer>=3.1.2',
    'ipaddr>=2.2.0',
    'jinxed>=1.2.0',
    'jmespath>=1.0.1',
    'prettytable>=3.6.0',
    'pyfiglet>=0.8.post1',
    'python-dateutil>=2.8.2',
    'python-editor>=1.0.4',
    'PyYAML>=6.0',
    'readchar==4.0.5',
    's3transfer>=0.6.0',
    'six>=1.16.0',
    'urllib3>=1.26.14',
    'wcwidth>=0.2.6',
]

setup(
    name='aws-vpc-cli',
    version='0.5.7',
    author='marcus16-kang',
    description='AWS VPC CloudFormation Stack Generator',
    author_email='marcus16-kang@outlook.com',
    license='MIT',
    entry_points={
        'console_scripts': [
            'vpc-cli=vpc_cli.main:main'
        ]
    },
    install_requires=requires,
    # packages=find_packages(),
    python_requires='>=3.8',
    url='https://github.com/marcus16-kang/vpc-stack-generator-cli',
    project_urls={
        'Source': 'https://github.com/marcus16-kang/vpc-stack-generator-cli'
    },
    include_package_data=True
)
