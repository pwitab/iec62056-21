from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

setup(
    name='iec62056-21',
    version='0.0.1-dev1',
    description='A Python library for IEC62056-21, Local Data Readout of Energy Meters. Former IEC1107',
    long_description=readme + '\n\n' + history,
    url='https://github.com/pwitab/mbus',
    author=('Henrik Palmlund Wahlgren '
            '@ Palmlund Wahlgren Innovative Technology AB'),
    author_email='henrik@pwit.se',
    license='BSD-3-Clause',
    packages=['iec62056_21'],
    install_requires=[],
    zip_safe=False,
    keywords=[],
    classifiers=[],

)
