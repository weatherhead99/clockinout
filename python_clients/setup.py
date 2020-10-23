from setuptools import setup, find_packages

setup(
      name="clockinout_client",
      version="0.0.1.dev0",
      packages = find_packages(),
      install_requires = ["nfcpy >= 1.0.3"])
