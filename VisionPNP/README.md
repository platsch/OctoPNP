# Disclaimer
VisionPNP is a image processing helper designed to provide necessarry functionality
to apply object detection on search images for SMD pick and place machines.
The repository is hosted on https://github.com/FKolwa/VisionPNP and was developed as 
part of a bachelor thesis at the University of Hamburg in 2019.

# Requirements
## opencv2
Clone and build the latest source of OpenCV. Just follow the [official
installation tutorial]("https://docs.opencv.org/master/index.html") regarding
your operating system.
The module has been tested with OpenCV versions >= 3.2.0.

Make sure that you build OpenCV for the appropriate Python version.
You can check this in the cmake configuration output.

## pybind11
Run a pip install for either python 2 or 3:
```
python -m pip install pybind11
```
or
```
python3 -m pip install pybind11
```
Apply sudo or --user if necessary.

# VisionPNP
## How to install
Just execute from within the project directory (including setup.py).
```
python -m pip install -e . --user
```
for python 2.7 or
```
python3 -m pip install -e . --user
```
for python >= 3.0.
Once the installation is complete make sure the module is recognized by python:
```
python -m pip list
```
or try to import it from the shell:
```
python
import VisionPNP
```

## How to use
Simply import VisionPNP and access methods by VisionPNP.<METHOD_NAME>(<PARAMS>)

Example:
```
import VisionPNP

maskValues = VisionPNP.getHSVColorRange('./images/gripper.png')
```
For a example scenarios take a look at *SampleApp.py*.

# Troubleshooting
## Problem -  Python can't find a library / missing symbol ImportError
The missing library cannot be found in the provided library folder or is
otherwise unknown and can't be linked. Setup.py finishes successfully but throws
an ImportError once imported into a python script.
Example :
```
ImportError: libopencv_core.so.4.1: cannot open shared object file: No such file or directory
```

## Solution - Add library path to ldconfig
Add missing library path to opencv libraries to LD_LIBRARY_PATH.
```
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib64/
```
Check availability.
```
ldconfig -N -v $(sed 's/:/ /g' <<< $LD_LIBRARY_PATH) | grep opencv
```
If the missing library is now showing up in the output you are good to go.

NOTE: This has to be redone on system restart when it is not permanently added to the
search paths! Library has to be of the same version as the one used to compile
the project.
