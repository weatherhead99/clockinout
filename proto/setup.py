from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from grpc_tools.command import BuildPackageProtos


class CustomBuild(build_py):
    def run(self):
        self.run_command("build_package_protos")
        build_py.run(self)



setup(
      name="clockinout_protocols",
      version="0.0.1.dev0",
      packages = find_packages(),
      package_dir = {"" : "."},
      cmdclass = {
          "build_py" : CustomBuild,
          "build_package_protos" : BuildPackageProtos},
      include_package_data=True)

