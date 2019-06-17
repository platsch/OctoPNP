import os
import numpy as np
import math
import argparse
from SmdParts import SmdParts
import re
import cv2

#------------------------------------------------
# Helper

# Return maximum point from vector coordinates
def _getMaximum(shape, pads):
  maxPosition = []
  # Maximum for shape
  maxPosition.append(np.amax(shape))
  maxPosition.append(abs(np.amin(shape)))
  # Maximum for pads
  maxPosition.append(np.amax(pads))
  maxPosition.append(abs(np.amin(pads)))
  # Overall maximum
  maxPosition = np.array(maxPosition, np.float)
  return np.amax(maxPosition)


# Converts XML vector coordinates to pixel coordinates
def _toPixelPoint(resolution, maximum, point):
  return (int(resolution * ((point[0] + maximum) / (maximum * 2))),
          int(resolution * ((point[1] + maximum) / (maximum * 2))))

#------------------------------------------------
# createTemplate method
# INPUT: array for shape and pads, square resolution for template (default 100px)
# OUTPUT: template image (numpy array)

def createTemplate(xmlShape, xmlPads, resolution=200):
  # create white template background
  templateImage = np.zeros([resolution,resolution,1],dtype=np.uint8)
  templateImage.fill(255)

  # convert arrays to numpy arrays
  shape = np.array(xmlShape, dtype=float)
  pads = np.array(xmlPads, dtype=float)

  # retrieve max value from coordinates
  maximum = _getMaximum(shape, pads)

  # create polygon from shape
  shapePoints = []
  for pos in shape:
    p = _toPixelPoint(resolution, maximum, (pos[0], pos[1]))
    shapePoints.append(p)

  # draw polygon
  pts = np.array(shapePoints, np.int32)
  cv2.fillPoly(templateImage,[pts],(0,0,0))

  # create rectangles from pads
  for pad in pads:
    # Convert template coordinates to pixel format
    p1 = _toPixelPoint(resolution, maximum, (pad[0], pad[1]))
    p2 = _toPixelPoint(resolution, maximum, (pad[2], pad[3]))
    # draw
    cv2.rectangle(templateImage, p1, p2, (0,0,0), -1)

  templateImage = cv2.copyMakeBorder(templateImage, 5, 5, 5, 5, cv2.BORDER_CONSTANT, None, (255,255,255))
  # Save image
  cv2.imwrite("template-output.png", templateImage)
  # Return image
  # return templateImage


#------------------------------------------------
# BEGIN DUMMY TEST SETUP

ap = argparse.ArgumentParser()
ap.add_argument("-g", "--gcode", required=True,
  help="path to input xml gcode file")
ap.add_argument("-i", "--id", required=True,
  help="id of component")
args = vars(ap.parse_args())

# parse provided XML from gcode file
xml = ""
f = open(args["gcode"], 'r')
for line in f:
    expression = re.search("<.*>", line)
    if expression:
        xml += expression.group() + "\n"
if xml:
    #check for root node existence
    if not re.search("<object.*>", xml.splitlines()[0]):
        xml = "<object name=\"defaultpart\">\n" + xml + "\n</object>"

# Setup parts
smdparts = SmdParts()
smdparts.load(xml)
ID=args["id"]

# SAMPLE EXECUTION
sh = smdparts.getPartShape(ID)
pa = smdparts.getPartPads(ID)

createTemplate(sh, pa)

# END DUMMY TEST SETUP
#------------------------------------------------