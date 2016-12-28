# -*- coding: utf-8 -*-
"""
    This file is part of OctoPNP

    OctoPNP is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OctoPNP is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with OctoPNP.  If not, see <http://www.gnu.org/licenses/>.

    Main author: Florens Wasserfall <wasserfall@kalanka.de>
"""

import cv2
import numpy as np
import math
import os
import shutil

class ImageProcessing:

	def __init__(self, box_size, bed_cam_binary_thresh, head_cam_binary_thresh):
		self.box_size=box_size
		self.bed_binary_thresh = bed_cam_binary_thresh
		self.head_binary_thresh = head_cam_binary_thresh
		self._img_path = ""
		self._last_saved_image_path = None
		self._last_error = ""
		self._interactive=False
		self._debug = True


# Locates a part in a box. Box size must be given to constructor. Image must contain only
# one box with white background.
# Returns displacement with respect to the center of the box if a part is detected, False otherwise.
# boolean relative_to_camera sets wether the offset should be relative to the box or to the camera.
#===================================================================================================
	def locatePartInBox(self,img_path, relative_to_camera):
		result = False

		self._img_path = img_path
		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)

		#DETECT BOUNDARY AND CROP
		crop_result = self._boundaryDetect(img)

		if not crop_result is None:
			crop_image = crop_result[0]
			crop_offset_x = crop_result[1]
			crop_offset_y = crop_result[2]

			gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
			ret,th_img = cv2.threshold(gray_img,self.head_binary_thresh,255,cv2.THRESH_BINARY_INV)
 			binary_img = self._removeBoxShadows(th_img)

			#GET CENTER OF MASS
			cmx, cmy = self._centerOfMass(binary_img)

			#TODO: check result from center of mass!

			#RETURN DISPLACEMENT
			n_rows=crop_image.shape[0]
			n_cols=crop_image.shape[1]
			displacement_x=(cmx-n_rows/2)*self.box_size/n_rows
			displacement_y=((n_cols-cmy)-n_cols/2)*self.box_size/n_cols
			if relative_to_camera:
				#incorporate the position of the tray box in relation to the image
				displacement_x += (crop_result[1] - (img.shape[0]-(crop_offset_x+n_rows)))/2 * self.box_size/n_rows
				displacement_y -= (crop_result[2] - (img.shape[1]-(crop_offset_y+n_cols)))/2 * self.box_size/n_cols
			result = displacement_x,displacement_y


			# Generate result image and return
			cv2.circle(crop_image,(int(cmx),int(cmy)), 5, (0,255,0), -1)
			filename="/finalcm_"+os.path.basename(self._img_path)
			finalcm_path=os.path.dirname(self._img_path)+filename
			cv2.imwrite(finalcm_path,crop_image)
			self._last_saved_image_path = finalcm_path

			if self._interactive: cv2.imshow("Part in box: ",crop_image)
			if self._interactive: cv2.waitKey(0)

		else:
			result = False

		return result


# Get part orientation by computing a rotated bounding box around contours
# and determining the main orientation of this box
# Returns the angle of main edges relativ to the
# next main axis [-45°:45°]
	def getPartOrientation(self,img_path):
		self._img_path = img_path

		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)
		
		rect = self._rotatedBoundingBox(img)

		# compute rotation offset
		rotation = rect[2]
		# normalize to positive PI range
		if rotation < 0:
			rotation = (rotation % -180) + 180

		rotation = rotation % 90
		result = -rotation if rotation < 45 else 90-rotation

		if self._debug: print "part deviation measured by bed camera: " + str(result)
		if self._interactive: cv2.imshow("contours",img)
		if self._interactive: cv2.waitKey(0)

		#save result as image for GUI
		filename="/orientation_"+os.path.basename(self._img_path)
		orientation_img_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(orientation_img_path, img)
		self._last_saved_image_path = orientation_img_path

		return result


# Find the position of a (already rotated) part. Returns the offset between the
# center of the image and the parts center of mass, 0,0 if no part is detected.
#==============================================================================
	def getPartPosition(self, img_path, pxPerMM):
		self._img_path = img_path

		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)

		rect = self._rotatedBoundingBox(img)

		cm_x = rect[0][0]
		cm_y = rect[0][1]

		res_x = img.shape[1]
		res_y = img.shape[0]

		displacement_x=(cm_x-res_x/2)/pxPerMM
		displacement_y=((res_y-cm_y)-res_y/2)/pxPerMM

		# write image for UI
		cv2.circle(img,(int(cm_x),int(cm_y)),5,(0,255,0),-1)
		filename="/final_"+os.path.basename(self._img_path)
		final_img_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(final_img_path,img)
		self._last_saved_image_path = final_img_path

		if self._interactive: cv2.imshow("Center of Mass",img)
		if self._interactive: cv2.waitKey(0)

		return [displacement_x, -displacement_y]

#==============================================================================
	def getLastSavedImagePath(self):
		if self._last_saved_image_path:
			return self._last_saved_image_path
		else:
			return False



#==============================================================================
	def getLastErrorMessage(self):
		return self._last_error



#==============================================================================
	def _boundaryDetect(self,img):
		result = True

		#Converting image to gray scale"
		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		row=np.shape(gray_img)[0]
		col=np.shape(gray_img)[1]


		canny_min_threshold = 50
		while canny_min_threshold > 20:
			canny_min_threshold = (canny_min_threshold/3)*2

			#Canny edge for line detection
			edges = cv2.Canny(gray_img,canny_min_threshold,canny_min_threshold*3,apertureSize = 3)

			#Hough Transform for line detection having minimum of max(row,col)/4
			lines = cv2.HoughLines(edges,1,np.pi/180,int(max(row,col)/4))

			ver_left_x=0
			hor_up_y=0
			width=row
			height=col

			list_rho_ver=[]
			list_rho_hor=[]

			#Drawing the lines
			if len(lines[0])>0:
				for rho,theta in lines[0]:
					theta_degree=(180/math.pi)*theta
					epsilon=2

					#Considering only the horizontal and vertical lines
					if 90-epsilon < int(theta_degree) < 90+epsilon:
						list_rho_hor.append(rho)
					elif 0-epsilon < int(theta_degree) < 0+epsilon:
						list_rho_ver.append(rho)

					#Drawing horizontal/vertical lines
					if (90-epsilon < int(theta_degree) < 90+epsilon) or (0-epsilon < int(theta_degree) < 0+epsilon):
						self._drawLine(img, rho, theta, (0, 255, 0))

				arr_rho_ver=np.sort(np.asanyarray(list_rho_ver))
				arr_rho_hor=np.sort(np.asanyarray(list_rho_hor))

				#Dividing the vertical lines into two parts
				rho_ver_part1=arr_rho_ver[arr_rho_ver<=int(col/2)]
				rho_ver_part2=arr_rho_ver[arr_rho_ver>int(col/2)]

				#Dividing the horizontal lines into two parts
				rho_hor_part1=arr_rho_hor[arr_rho_hor<=int(row/2)]
				rho_hor_part2=arr_rho_hor[arr_rho_hor>int(row/2)]

				#found boundaries?
				if len(rho_ver_part1) > 0 and len(rho_ver_part2) > 0 and len(rho_hor_part1) > 0 and len(rho_hor_part2) > 0:
					#Finding the boundary box
					ver_left_x=np.max(rho_ver_part1)
					hor_up_y=np.max(rho_hor_part1)
					width=np.min(rho_ver_part2)-ver_left_x
					height=np.min(rho_hor_part2)-hor_up_y
					result = True
					break
				else:
					result = None
					continue
			else:
				result = None
				continue


		if result:
			cv2.rectangle(img,(ver_left_x,hor_up_y),(ver_left_x+width,hor_up_y+height),(255,0,0),2)

			print "Bounding box details:"
			print "x0,y0: " + str(ver_left_x) + str(hor_up_y)
			print "width: " + str(width)
			print "height: " + str(height)
		else:
			self._last_error = "No box-boundary detectable"

		if self._interactive: cv2.imshow("Hough Lines",img)
		if self._interactive: cv2.waitKey(0)

		#Crop image and write
		img_crop=img[int(hor_up_y):int(hor_up_y+height), int(ver_left_x):int(ver_left_x+width)]
		filename="/cropped_"+os.path.basename(self._img_path)
		cropped_boundary_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(cropped_boundary_path,img_crop)
		self._last_saved_image_path = cropped_boundary_path
		if result:
			result = [img_crop, ver_left_x,hor_up_y]
		return result


#=============================================================================
	def _removeBoxShadows(self, binary_img):

		res_y = binary_img.shape[0]
		res_x = binary_img.shape[1]

		for i in range(res_y):
			k = 0
			while (binary_img[i,k] > 1 and k < res_x-1):
				binary_img[i,k] = 0
				k += 1

			k = res_x-1
			while (binary_img[i,k] > 1 and k > 0):
				binary_img[i,k] = 0
				k -= 1

		if self._interactive: cv2.imshow("Binarized image",binary_img)
		if self._interactive: cv2.waitKey(0)

		return binary_img

#=========================================================================
	def _rotatedBoundingBox(self, img):
		#convert image to grey and blur
		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		gray_img=cv2.blur(gray_img, (3,3))

		ret, binary_img = cv2.threshold(gray_img, self.bed_binary_thresh, 255, cv2.THRESH_BINARY)
		contours, hierarchy = cv2.findContours(binary_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE, (0, 0));

		#cv2.drawContours(img, contours, -1, (0,255,0), 3) # draw basic contours

		minArea = 20; # how to find a better value??? input from part description?
		maxArea = gray_img.shape[0] * gray_img.shape[1] * 0.8 # Y*X | don't detect full image

		rectPoints = [];

		for contour in contours:
			rect = cv2.minAreaRect(contour)
			rectArea = rect[1][0] * rect[1][1]
			if(rectArea > minArea and rectArea < maxArea):
				box = cv2.cv.BoxPoints(rect)
				for point in box:
					rectPoints.append(np.array(point, dtype=np.int32))
				#box = np.int0(box)
				#cv2.drawContours(img,[box],0,(0,0,255),2)
			#cv2.imshow("contours",img)
			#cv2.waitKey(0)

		rectArray = np.array(rectPoints)
		rect = cv2.minAreaRect(rectArray)

		# draw rotated bounding box for visualization
		box = cv2.cv.BoxPoints(rect)
		box = np.int0(box)
		cv2.drawContours(img,[box],0,(0,0,255),2)

		return rect


#=========================================================================
	def _centerOfMass(self, binary_img):
		cm_x = 0
		cm_y = 0

		res_x = binary_img.shape[1]
		res_y = binary_img.shape[0]
		object_pixels = sum(binary_img[(binary_img>0)])/255
		sum_x = []


		#TODO: Use built-in histograms or similar to speed this up!!
		for i in range(res_x):
			cm_x += sum(binary_img[:, i])/(255.0*object_pixels)*i

		for i in range(res_y):
			cm_y += sum(binary_img[i, :])/(255.0*object_pixels)*i

		cm_x = int(round(cm_x))
		cm_y = int(round(cm_y))

		return cm_x, cm_y


# Draw a line to the given image. Modifies the image!!!
#============================================================================
	def _drawLine(self, img, rho, theta, color):
		a = np.cos(theta)
		b = np.sin(theta)
		x0 = a*rho
		y0 = b*rho
		x1 = int(x0 + 1000*(-b))
		y1 = int(y0 + 1000*(a))
		x2 = int(x0 - 1000*(-b))
		y2 = int(y0 - 1000*(a))
		cv2.line(img,(x1,y1),(x2,y2),color,2)