import VisionPNP
import cv2
import numpy as np

#---------<
# Input images
headCamImage = cv2.imread('./resources/resistor_on_tray.png')
bedCamImageFindShape = cv2.imread('./resources/resistor_on_gripper.png')
bedCamImageMatchTemplate = cv2.imread('./resources/tiny_on_gripper.png')
templateImage = cv2.imread('./resources/template_fake.png', cv2.IMREAD_GRAYSCALE)

searchImageDummy = cv2.imread('./resources/pic1.png', cv2.IMREAD_GRAYSCALE)
templateImageDummy = cv2.imread('./resources/templ.png', cv2.IMREAD_GRAYSCALE)

#---------<
# Scenario 1 - Find position of object in tray picture
#---------<
# Read the HSV color range from a background image
maskValues = VisionPNP.getHSVColorRange('./resources/gripper.png')

# Create a binarized image of th input containing only the areas within the
# provided color mask (black)
maskImage = VisionPNP.createColorRangeMask(headCamImage, maskValues)

# Crop the input image to the shape of the provided mask
croppedImage = VisionPNP.cropImageToMask(headCamImage, maskImage)

# Find the position of a single object inside the provided image
position = VisionPNP.findShape(croppedImage)
cv2.circle(croppedImage,(position[0], position[1]), 4, (0,0,255), -1)
cv2.imwrite('./OUTPUT_scenario_1.png', croppedImage)
print(position)

#---------<
# Scenario 1B - Extract bouding rect from mask, then use rect to crop image.
#---------<
# Extract bouding rect fom binarized mask image
bRect = VisionPNP.findContainedRect(maskImage)
croppedImage1B = VisionPNP.cropImageToRect(headCamImage, bRect)

cv2.imwrite('./OUTPUT_scenario_1B.png', croppedImage1B)

#---------<
# Scenario 2 - Find position of object in gripper image (no orientation)
#---------<
# Clean green background
cleanedBedCam = VisionPNP.binaryFromRange(bedCamImageFindShape, maskValues)

# # Find center of mass
center = VisionPNP.findShape(cleanedBedCam)
cv2.circle(bedCamImageFindShape,(center[0], center[1]), 4, (0,0,255), -1)
cv2.imwrite('./OUTPUT_scenario_2.png', bedCamImageFindShape)
print(center)

#---------<
# Scenario 3 - Find template in search image (with orientation)
#---------<
# Find a binary template inside a provided input image.
# The maskValues contain the color range of the background color for easier seperation.
# Return its orientation.
searchImageCopy = cv2.imread("./resources/tiny_on_gripper.png")
templateImageCopy = cv2.imread("./resources/template_output.png")

# Returns vector of x-position, y-position, width (in pixels) and rotation of the template found in the search image
cleanedSearchImage = VisionPNP.binaryFromRange(searchImageCopy, maskValues)
# cv2.imwrite('./cleanedImage.png', cleanedSearchImage)
bestCandidate = VisionPNP.matchTemplate(searchImageCopy, templateImageCopy, maskValues, 374)
candidateImage = VisionPNP.drawCandidate(searchImageCopy, templateImageCopy, bestCandidate)
cv2.imwrite("./OUTPUT_scenario_3.png", candidateImage)
print(bestCandidate)
