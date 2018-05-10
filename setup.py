import os

from setuptools import setup, find_packages

def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
  name = "hyper4_control_project",
  version = "0.1.0",
  author = "David Hancock",
  author_email = "dhancock@cs.utah.edu",
  description = ("Controller and associated tools for the HyPer4 virtualized "
                 "programmable data plane"),
  license = "MIT",
  keywords = "p4 vpdp controller",
  packages=find_packages(),
  long_description=read('README.txt'),
  classifiers=[
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Topic :: System :: Networking",
  ],
)
