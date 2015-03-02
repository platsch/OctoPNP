# OctoPNP
OctoPNP is an OctoPrint plugin for camera assisted pick 'n place applications in 3D-Printers.

# Introduction
OctoPNP is an extension that allows Octoprint to control printers and similar devices with additional hardware for handling of SMD-parts.
It currently requires the following hardware extensions:
* A Tray consisting of a grid of boxes to store SMD parts in a defined position
* A head camera to locate the exact part position on the tray
* A (second) bed camera to precisely align the parts during the placing operation
* A vaccum nozzle to grip parts

# Installation
## Prerequirements
To achieve higher compatibility and modularity, OctoPNP doesn't acces the cameras directly. Every time an image is required, OctoPNP executes the script `octoprint_OctoPNP/cameras/grab.sh`. This script must be adapted for every installation according to the deployed camera setup. OctoPNP expects a set of cropped and rotated images in the `octoprint_OctoPNP/cameras` folder, filenames and path can be set in the settings dialog.

## Installing the package
The plugin itself can be installed as any regular python package:
`pip install https://github.com/platsch/OctoPPNP/archive/master.zip`

Make sure you use the same Python environment that you installed OctoPrint under, otherwise the plugin won't be able to satisfy its dependencies. Further information can be found in the Octoprint [documentation](http://docs.octoprint.org/en/devel/plugins/using.html)

## Data Format
The information for the PNP system is integrated into normal gcode files as a commented XML favor somewhere in the gcode. OctoPNP extracts the required information automatically everytime a gcode file is loaded in Octoprint. Example files are include in the `utils` folder. The XML structure is still under development and will probably change during the next months. The comment-semicolon causes Octoprint to ignore the SMD-data.

```XML
;normal printing commands
G1 X10 F3000
G1 Y10 F3000
G1 Z5 F3000

;pick part nr 2 and place it to the destination given in the XML description
M361 P2

;description of the actual parts
;<object name="simple_lines">
;<part id="1" name="LED_1206">
;  <position box="5"/>
;  <size height="1.05"/>
;  <shape>
;    <point x="value" y="value"/>
;    <point x="value2" y="value2"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="104.938" y="27.987" orientation="90"/>
;</part>


;<part id="2" name="RES_1206">
;  <position box="6"/>
;  <size height="0.5"/>
;  <shape>
;    <point x="value" y="value"/>
;    <point x="value2" y="value2"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="104.938" y="27.987" orientation="90"/>
;</part>

;<part id="4" name="ATTINY">
;  <position box="4"/>
;  <size height="1.95"/>
;  <shape>
;    <point x="0.1" y="1.5"/>
;    <point x="-2" y="0"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="90.938" y="20" orientation="45"/>
;</part>
;</object>
```
