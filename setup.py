from setuptools import setup, find_packages

setup(
    name='vpc-cli',
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
    packages=find_packages(),
    python_requires='>=3.7',
    url='https://github.com/marcus16-kang/vpc-stack-generator-cli'
)
