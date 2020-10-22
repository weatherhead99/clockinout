from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.command.install import install
from grpc_tools.command import BuildPackageProtos

class RunProtoBuildBefore:
    def run(self):
        self.run_command("build_package_protos")
        return super().run()


class CustomDevelop(RunProtoBuildBefore, develop):...
class CustomInstall(RunProtoBuildBefore, install):...
class CustomBuild(RunProtoBuildBefore, build_py):...

setup(
      name="clockinout_protocols",
      version="0.0.1.dev0",
      packages = find_packages(),
      package_dir = {"" : "."},
      cmdclass = {
          "build_package_protos" : BuildPackageProtos,
          "build_py" : CustomBuild,
          "develop" : CustomDevelop,
          "install" : CustomInstall
          },
      include_package_data=True)

