from setuptools import setup, find_packages

requires = [
    'ansicon==1.89.0',
    'blessed==1.19.1',
    'inquirer==2.10.0',
    'ipaddr==2.2.0',
    'jinxed==1.2.0',
    'prettytable==3.4.1',
    'pyfiglet==0.8.post1',
    'python-editor==1.0.4',
    'PyYAML==6.0',
    'readchar==4.0.3',
    'six==1.16.0',
    'wcwidth==0.2.5',
]

setup(
    name='aws-vpc-cli',
    version='0.1.2',
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
    python_requires='>=3.7',
    url='https://github.com/marcus16-kang/vpc-stack-generator-cli',
    project_urls={
        'Source': 'https://github.com/marcus16-kang/vpc-stack-generator-cli'
    }
)
