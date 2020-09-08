# OctoPNP
OctoPNP is an OctoPrint plugin for camera assisted pick 'n place applications in 3D-Printers.

# Introduction
OctoPNP is an extension that allows Octoprint to control printers and similar devices with additional hardware for handling of SMD-parts.
It currently requires the following hardware extensions:
* A Tray consisting of a grid of boxes to store SMD parts in a defined position
* A head camera to locate the exact part position on the tray
* A (second) bed camera to precisely align the parts during the placing operation
* A vacuum nozzle to grip parts

![octopnp_screenshot](https://user-images.githubusercontent.com/4190756/35239671-7f378542-ffb1-11e7-9a77-4b9868aa3845.png)

# Installation
## Prerequirements
To achieve higher compatibility and modularity, OctoPNP doesn't acces the cameras directly. Every time an image is required, OctoPNP executes a user defined script which must be adapted for every installation according to the deployed camera setup. OctoPNP expects a set of correctly cropped and rotated images after executing the script. Filenames and path for images and script must be set in the settings dialog.
The calibration feature supports direct camera access via http requests to generate a live view e.g. via mjpg_streamer.

## OpenCV on embedded hardware (Raspberry Pi)
OctoPNP requires `numpy`and `OpenCV`, both are listed in the `requirements.txt` and should be automatically resolved via pip during installation.
However, on many embedded systems, including the RasPi, opencv-python is not available.
To solve this:
* Remove (or comment) the `opencv-python` line in `requirements.txt`
* Manually install OpenCV on your system ([official tutorial](https://docs.opencv.org/master/d7/d9f/tutorial_linux_install.html)). This should build OpenCV packages for Python 2 and 3 if both versions are installed on the system.
* If OctoPrint is installed in a virtual environment (as recommended), at least in some cases the OpenCV library must be linked (or copied) into the venv like this:
```
ln -s /usr/local/lib/python3.6/dist-packages/cv2/python-3.6/cv2.cpython-36m-arm-linux-gnueabihf.so ~/OctoPrint/venv3/lib/python3.6/site-packages/
```


## Installing the package
The plugin itself can be installed as any regular python package:
`pip install https://github.com/platsch/OctoPNP/archive/master.zip`

Make sure you use the same Python environment that you installed OctoPrint under, otherwise the plugin won't be able to satisfy its dependencies. Further information can be found in the Octoprint [documentation](http://docs.octoprint.org/en/stable/plugins/distributing.html#proper-packages-installable-via-pip)
OctoPNP requires numpy and opencv2. Try installing those packages by hand if automatic dependency resolving failes.

## Data Format
The information for the PNP system is integrated into normal gcode files as a commented XML flavor somewhere in the gcode. OctoPNP extracts the required information automatically everytime a gcode file is loaded in Octoprint. Example files are included in the `utils` folder. The XML structure is still under development and will probably change during the next months. The comment-semicolon causes Octoprint to ignore the SMD-data.

```XML
;normal printing commands
G1 X10 F3000
G1 Y10 F3000
G1 Z5 F3000

;pick part nr 2 and place it to the destination given in the XML description
M361 P2

;description of the actual parts
;<object name="simple_lines">
;<part id="1" name="ATTINY">
;  <position box="1"/>
;  <size height="1"/>
;  <shape>
;    <point x="-2.6" y="-3.4"/>
;    <point x="-2.6" y="3.4"/>
;    <point x="2.6" y="3.4"/>
;    <point x="2.6" y="-3.4"/>
;  </shape>
;  <pads>
;    <pad x1="-2.155" y1="-4.254" x2="-1.655" y2="-2.054"/>
;    <pad x1="-0.895" y1="-4.254" x2="-0.395" y2="-2.054"/>
;    <pad x1="0.375" y1="-4.254" x2="0.875" y2="-2.054"/>
;    <pad x1="1.645" y1="-4.254" x2="2.145" y2="-2.054"/>
;    <pad x1="-2.155" y1="2.054" x2="-1.655" y2="4.254"/>
;    <pad x1="-0.885" y1="2.054" x2="-0.385" y2="4.254"/>
;    <pad x1="0.385" y1="2.054" x2="0.885" y2="4.254"/>
;    <pad x1="1.655" y1="2.054" x2="2.155" y2="4.254"/>
;  </pads>
;  <destination x="100" y="90" z="2.75" orientation="90"/>
;</part>
;
;<part id="2" name="RES_1206">
;  <position box="2"/>
;  <size height="1"/>
;  <shape>
;    <point x="-1.6891" y="-0.8763"/>
;    <point x="-1.6891" y="0.8763"/>
;    <point x="1.6891" y="0.8763"/>
;    <point x="1.6891" y="-0.8763"/>
;  </shape>
;  <pads>
;    <pad x1="0.622" y1="-0.9015" x2="2.222" y2="0.9015"/>
;    <pad x1="-2.222" y1="-0.9015" x2="-0.622" y2="0.9015"/>
;  </pads>
;  <destination x="108.304" y="90.674" z="2.75" orientation="0"/>
;</part>
;</object>
```
# Configuration
Good configuration and calibration of the printer is absolutely crucial to successfully use multiple extruders and cameras.
## Tray
The tray-position is set in relation to the primary extruder (usually the plastic extruder). To find the position, move the primary extruder to the bottom left corner of the tray and note the position. A negative Z-offset can be used if the tray is lower than the printbed.

![octopnp_settings_tray_small](https://cloud.githubusercontent.com/assets/4190756/12114966/9a0747d2-b3ae-11e5-93e0-79d14a2ee632.png)

## Extruders / Nozzles
The minimal setup requires 3 nozzles:
* The plastic extruder to print the object (primary extruder)
* An Extruder for liquids to print the conductive wires
* A vacuum nozzle to grip SMD-parts

The offset is always relative to the primary extruder. Offsets can be handled by the slicer, by OctoPNP or by the printer firmware. 
The offset for the liquid extruder must be handled by the slicer or by the firmware, OctoPNP is not aware of this extruder. Firmware offset is encouraged to avoid frequent G-code generation, since for most setups the offset has to be re-calibrated at least after every refill of the extruder. OctoPNP provides the calibration tool to quickly correct the firmware offset.
The offset for the vacuum nozzle must be handled by OctoPNP or by the firmware.
## Cameras
### Position
The camera position is relative to the primary nozzle for the head camera (this camera is mounted somewhere next to the extruder at the X-axis and follows the printheads movements). The bed camera is mounted to the printers frame, the camera position is absolute and again relative to the primary extruder.
* `Focus distance` defines the printbead Z-position for the optimal focus point. 
* The `px/mm` value is used by the image processing to measure offsets and only required for the bed camera, since the head camera utilizes the known box size for on demand calibration.
* The `binarization threshold` is used by the image processing to seperate object and background. The value depends on the camera and illumination, currently there is no good calibration method.
* `Image path` and `grab script path` denote the locations of script and preprocessed images as described in the Prerequirements section.
* `http-path` can be used if the camera provides an http interface (e.g. with mjpg_streamer). This is only used to generate a live view during calibration, not for actual pick and place operations. Leave empty to use the script base method for calibration. Note that for technical reasons only still-images can be used, mjpg streams or other video formats are not supported!

### Image acquisition
The `cameras` folder contains simple scripts to fetch single images from
* any camera which can be accessed with an http get command (http)
* Basler industrial cameras supporting the pylon framework (pylon, tested with Pilot and Ace models)

## Calibration wizard
The calibration "wizard" is an experimental set of tools to quickly achieve several calibration tasks with high precision.
* Calibration of extruders is done by printing a defined pattern (e.g. a cross) on the printbed. To calibrate an offset, the head camera moves to the printed pattern (position given by user) and the user uses the arrows keys to correct possible offsets by using the camera image superimposed by cross hairs. Offsets between extruders can be directly saved to the eeprom if a repetier firmware is used.
* The tray position can be calibrated similar by moving the camera to the corners and correcting possible offsets with manual key control.
* The bed camera can be calibrated against any calibrated extruder that is able to move over the camera. While some extruders contain sticky, liquid content, it might be a good idea to cover the camera with some glass.
* With a calibrated bed camera any extruder that is able to move over the camera, including the vacuum nozzle, can be calibrated.

![octopnp_settings_calibration_small](https://cloud.githubusercontent.com/assets/4190756/12115026/fe216f54-b3ae-11e5-9a04-4f83776c2cf6.png)
