# -*- coding: utf-8 -*-
"""
Created on Tue Feb 17 02:12:51 2015

@author: soubarna
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
#===================================================================================================
	def locatePartInBox(self,img_path):
		result = False

		self._img_path = img_path
		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)

		#DETECT BOUNDARY AND CROP
		crop_image=self._boundaryDetect(img)

		gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
		ret,th_img = cv2.threshold(gray_img,self.head_binary_thresh,255,cv2.THRESH_BINARY_INV)
 		binary_img = self._removeBoxShadows(th_img)

		if not crop_image is None:
			#GET CENTER OF MASS
			cmx, cmy = self._centerOfMass(binary_img)

			#TODO: check result from center of mass!

			#RETURN DISPLACEMENT
			n_rows=crop_image.shape[0]
			n_cols=crop_image.shape[1]
			displacement_x=(cmx-n_rows/2)*self.box_size/n_rows
			displacement_y=((n_cols-cmy)-n_cols/2)*self.box_size/n_cols
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

# Find orientation of a part in the given Image. Returns the angle of main edges relativ to the
# next main axis (0-45°) or 0 if no part can be detected.
#==============================================================================
	def getPartOrientation(self,img_path):
		self._img_path = img_path

		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)
		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

		canny_min_threshold = 250
		while canny_min_threshold > 10:
			lines, len_diagonal = self._extractLines(gray_img, canny_min_threshold)
			canny_min_threshold = (canny_min_threshold/3)*2
			if len(lines) < 5:
				continue

			arr_theta=[]

			#drawing the lines and calculating orientation and offset

			for rho,theta in lines:
				theta_degree=(180/math.pi)*theta
				if theta_degree>90:
					arr_theta.append(90+(180-theta_degree))
				elif theta_degree<=90:
					arr_theta.append(90-theta_degree)

				#draw lines
				self._drawLine(img, rho, theta, (0, 255, 0))


			##calculating deviation
			dev=[]
			for theta in arr_theta:
				if theta>=0 and theta <=45:
					dev.append(theta)
				elif theta>=135 and theta<=180:
					dev.append(theta-180)
				else:
					dev.append(theta-90)

			arr_deviation=np.asanyarray(dev)
			avg_deviation=np.average(arr_deviation)

			if self._debug: print "avg deviation: " + str(avg_deviation)
			break

		if self._interactive: cv2.imshow("Lines orientation",img)
		if self._interactive: cv2.waitKey(0)

		#save result as image for GUI
		filename="/orientation_"+os.path.basename(self._img_path)
		orientation_img_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(orientation_img_path,img)
		self._last_saved_image_path = orientation_img_path


		return avg_deviation


# Find the position of a (already rotated) part. Returns the offset between the
# center of the image and the parts center of mass, 0,0 if no part is detected.
#==============================================================================
	def getPartPosition(self, img_path, pxPerMM):
		self._img_path = img_path

		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)

		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

		cm_x = 0
		cm_y = 0

		ret,th1 = cv2.threshold(gray_img,self.bed_binary_thresh,255,cv2.THRESH_BINARY_INV)

		if self._interactive: cv2.imshow("Binarized image",th1)
		if self._interactive: cv2.waitKey(0)

		cm_x, cm_y = self._centerOfMass(th1)

		res_x = th1.shape[1]
		res_y = th1.shape[0]

		displacement_x=(cm_x-res_x/2)/pxPerMM
		displacement_y=((res_y-cm_y)-res_y/2)/pxPerMM

		# write image for UI
		cv2.circle(img,(cm_x,cm_y),5,(0,255,0),-1)
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

					#Considering only the horizontal and ve150rtical lines
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
			result = img_crop
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


# Finds lines in the given image by applying a Canny operator and a Hough transformation.
# Returns an array of lines and the estimated diameter of the object.
#==============================================================================
	def _extractLines(self, gray_img, low_threshold):

		ret,binary_img = cv2.threshold(gray_img,self.bed_binary_thresh,255,cv2.THRESH_BINARY_INV)
		object_pixels = sum(binary_img[(binary_img>0)])/255
		len_diagonal = math.sqrt(object_pixels)

		#ratio to reduce line length for hough transformation if the part is large
		object_img_ratio = float(math.sqrt(object_pixels))/math.sqrt((binary_img.shape[0]*binary_img.shape[1]))

		if self._interactive: cv2.imshow("Binary img",binary_img)
		if self._interactive: cv2.waitKey(0)

		#Detect Lines
		#edges = cv2.Canny(gray_img,50,150,apertureSize = 3)
		edges = cv2.Canny(gray_img,low_threshold,low_threshold*3,apertureSize = 3)
		if self._interactive: cv2.imshow("Lines orientation",edges)
		if self._interactive: cv2.waitKey(0)


		#lines = cv2.HoughLines(edges,2,np.pi/180,int(len_diagonal/4))
		lines = cv2.HoughLines(edges,1,np.pi/180,int(len_diagonal/(2+2*object_img_ratio)))
		if lines is None:
			lines = [[]]
		return lines[0], len_diagonal

# Computes the intersection point of two lines in polar representation
#==============================================================================
	def _polarIntersect(self,line1,line2):
		theta1=line1[0]
		r1=line1[1]
		theta2=line2[0]
		r2=line2[1]

		a=np.array([[np.cos(theta1),np.cos(theta2)],[np.sin(theta1),np.sin(theta2)]])

		r=np.array([r1,r2])
		a_inv=np.linalg.inv(a)
		arr=np.dot(r,a_inv)

		return arr

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