from setuptools import setup, find_packages

requires = [
    'ipaddr',
    'prettytable',
    'prompt-toolkit',
    'pyfiglet',
    'Pygments',
    'PyInquirer',
    'PyYAML',
    'regex',
    'six',
    'wcwidth'
]

setup(
    name='aws-vpc-cli',
    version='0.0.1',
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
    packages=find_packages(),
    python_requires='>=3.7',
    url='https://github.com/marcus16-kang/vpc-stack-generator-cli',
    project_urls={
        'Source': 'https://github.com/marcus16-kang/vpc-stack-generator-cli'
    }
)
