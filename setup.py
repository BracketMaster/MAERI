from setuptools import setup, find_packages
import sys
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
NEWS = open(os.path.join(here, 'NEWS.md')).read()


version = '0.1'

install_requires = [
    'nmigen @ git+https://github.com/nmigen/nmigen.git',
    'luna @ git+https://github.com/greatscottgadgets/luna',
    'termcolor',
    #'mkdocs',
    'numpy',
]

setup(
    name='maeri',
    version=version,
    description="Synthesizeable RTL for executing CNNs from Keras.",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: LGPLv3+",
        "Programming Language :: Python :: 3",
    ],
    keywords='Keras CNN Accelerator nMigen RTL',
    author='Yehowshua Immanuel',
    author_email='yehowshua@chipeleven.org',
    # TODO : UPDATE!
    #url='https://github.com/BracketMaster/MAERIV6',
    license='GPLv3+',
    #package_data={
    #    "maeriv6": ["visualiser_frontend/reduction_network/frontend/frontend.js"],
    #    "maeriv6": ["visualiser_frontend/reduction_network/frontend/frontend.html"]
    #    },
    #include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)
