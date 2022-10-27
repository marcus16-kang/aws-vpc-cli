from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='vpc-cli',
    version='0.0.1',
    author='marcus16-kang',
    description='AWS VPC CloudFormation Stack Generator',
    long_description=long_description,
    long_description_content_type='text/markdown',
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
