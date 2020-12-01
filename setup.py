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
    'setuptools',
    'wheel',
    'onnx',
    #'onnxruntime',
    'numpy',
    #'scipy',
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
    keywords='ONNX CNN Accelerator nMigen RTL',
    author='Yehowshua Immanuel',
    author_email='yehowshua@chipeleven.org',
    # TODO : UPDATE!
    url='https://github.com/BracketMaster/maeri',
    license='GPLv3+',
    zip_safe=False,
    install_requires=install_requires,
)
