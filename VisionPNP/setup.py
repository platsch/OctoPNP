import os, sys

from distutils.core import setup, Extension
from distutils import sysconfig

module = Extension(
    'VisionPNP',
    sources = [
      './src/python_module.cpp',
      './src/color.cpp',
      './src/image.cpp',
      './src/hough.cpp'
    ],
    include_dirs = [
      '/usr/local/include/pybind11',
      '/usr/local/include/opencv4',
      './src'
    ],
    library_dirs = [
      '/usr/local/lib64'
    ],
    libraries = [
      'opencv_core',
      'opencv_highgui'
    ],
    language='c++',
    extra_compile_args = ['-std=c++14', '-fPIC'],
    )

setup(
    name = 'VisionPNP',
    version = '0.1',
    description = 'TODO',
    install_requires=[
        'pybind11'
    ],
    ext_modules = [module],
)
