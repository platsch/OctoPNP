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
#import scipy.signal as sig
from matplotlib import pyplot as plt

class ImageProcessing:

	def __init__(self, box_size):
		self.box_size=box_size
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
		img=cv2.imread(img_path,cv2.CV_LOAD_IMAGE_COLOR)

		#DETECT BOUNDARY AND CROP
		crop_image=self._boundaryDetect(img)
		if not crop_image is None:
			#GET CENTER OF MASS
			gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
			cmx,cmy = self._centerofMass(gray_img)[0:2]

			#TODO: check result from center of mass!

			#RETURN DISPLACEMENT
			n_rows=crop_image.shape[0]
			n_cols=crop_image.shape[1]
			displacement_x=(cmx-n_rows/2)*self.box_size/n_rows
			displacement_y=((n_cols-cmy)-n_cols/2)*self.box_size/n_cols
			result = displacement_x,displacement_y
		else:
			result = False

		return result

# Find orientation of a part in the given Image. Returns the angle of main edges relativ to the
# next main axis (0-45°) or 0 if no part can be detected.
#==============================================================================
	def getPartOrientation(self,img_path):
		self._img_path = img_path

		# open image file
		img=cv2.imread(img_path,cv2.CV_LOAD_IMAGE_COLOR)
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
		img=cv2.imread(img_path,cv2.CV_LOAD_IMAGE_COLOR)

		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

		cm_x = 0
		cm_y = 0

		ret,th1 = cv2.threshold(gray_img,200,255,cv2.THRESH_BINARY_INV)

		res_x = th1.shape[1]
		res_y = th1.shape[0]
		object_pixels = sum(th1[(th1>0)])/255
		sum_x = []


		#TODO: Use built-in histograms or similar to speed this up!!
		for i in range(res_x):
			cm_x += sum(th1[:, i])/(255.0*object_pixels)*i

		for i in range(res_y):
			cm_y += sum(th1[i, :])/(255.0*object_pixels)*i

		cm_x = int(round(cm_x))
		cm_y = int(round(cm_y))

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



# Find the position of a (already rotated) part. Returns the offset between the
# center of the image and the parts center of mass, 0,0 if no part is detected.
# This method is deprecated but might give better results in some setups
#==============================================================================
	def getPartPositionFromLineDetection(self,img_path, pxPerMM):

		self._img_path = img_path

		# open image file
		img=cv2.imread(img_path,cv2.CV_LOAD_IMAGE_COLOR)

		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

		cm_x = 0
		cm_y = 0

		canny_min_threshold = 200
		while canny_min_threshold > 20:
			lines, len_diagonal = self._extractLines(gray_img, canny_min_threshold)
			canny_min_threshold = (canny_min_threshold/4)*3
			print "Canny min threshold: " + str(canny_min_threshold)

			if len(lines) < 4: #not enough lines for a square...
				print "CenterOfMass: not enough lines, decreasing Canny threshold"
				continue

			list_theta=[]
			list_rho=[]

			for rho,theta in lines:
				if rho <0:
					list_theta.append(np.pi+theta)
					list_rho.append(-rho)

				else:
					list_theta.append(theta)
					list_rho.append(rho)

			arr_theta=np.asanyarray(list_theta)
			arr_rho=np.asanyarray(list_rho)

			coordinate_x=[]
			coordinate_y=[]
			points = []
			epsilon = 5

			#Intersection of lines having angle diff in the range (85-95) or (265-275)
			for i in range(0,len(arr_rho),1):
				for j in range(0,len(arr_rho),1):
					angle_diff=np.rad2deg(abs(arr_theta[i]-arr_theta[j]))

					if i!=j and (angle_diff>=90-epsilon and angle_diff<=90+epsilon) or (angle_diff>=270-epsilon and angle_diff<=270+epsilon):
						line1=np.array([arr_theta[i],arr_rho[i]])
						line2=np.array([arr_theta[j],arr_rho[j]])
						x,y=self._polarIntersect(line1,line2)
						coordinate_x.append(int(x))
						coordinate_y.append(int(y))
						points.append([int(round(x)), int(round(y))])

						#visualisation
						self._drawLine(img, arr_rho[i], arr_theta[i], (0, 255, 0))
						#visualisation
			if len(coordinate_x) < 2 or len(coordinate_y) < 2:
				print "CenterOfMass: not enough intersections, decreasing Canny threshold"
				continue

			pointArray = np.asanyarray(points)
			hull = cv2.convexHull(pointArray)

			#visualisation
			for p in range(0,len(hull), 1):
				q = (p+1)%len(hull)
				cv2.line(img,(hull[p][0][0],hull[p][0][1]),(hull[q][0][0], hull[q][0][1]),(0,0,int(canny_min_threshold)),2)

			area = math.sqrt(cv2.contourArea(hull))

			min_x = np.min(coordinate_x)
			max_x = np.max(coordinate_x)
			min_y = np.min(coordinate_y)
			max_y = np.max(coordinate_y)

			#Center of mass
			cm_x=int((min_x+max_x)/2)
			cm_y=int((min_y+max_y)/2)

			print "area: " + str(area) + " len_diagonal/2: " + str(len_diagonal/2)
			if self._interactive: cv2.imshow("Canny Image",img)
			if self._interactive: cv2.waitKey(0)
			if area > len_diagonal/2:
				break

			print "CenterOfMass: bounding box to small, decreasing Canny threshold"


		#CALCULATING DISPLACEMENT
		n_rows=img.shape[0]
		n_cols=img.shape[1]
		if canny_min_threshold < 20:
			print "CenterOfMass: no part found, use 0:0 as default CoM"
			cm_x = n_rows/2
			cm_y = n_cols/2
			print "cm_x: " + str(cm_x)

		displacement_x=(cm_x-n_rows/2)/pxPerMM
		displacement_y=((n_cols-cm_y)-n_cols/2)/pxPerMM

		# write image for UI
		cv2.circle(img,(cm_x,cm_y),5,(0,255,0),-1)
		filename="/final_"+os.path.basename(self._img_path)
		final_img_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(final_img_path,img)
		self._last_saved_image_path = final_img_path

		if self._interactive: cv2.imshow("Canny Image",img)
		if self._interactive: cv2.waitKey(0)


		#
		#
		# self._img_path = img_path
		# # open image file
		# img=cv2.imread(img_path,cv2.CV_LOAD_IMAGE_COLOR)
		#
		# cx, cy=self._centerofMass(img)[0:2]
		#
		# np.shape(img)
		# n_rows=img.shape[0]
		# n_cols=img.shape[1]
		# displacement_x=(cx-n_rows/2)/pxPerMM
		# displacement_y=(n_cols/2-cy)/pxPerMM

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
			cv2.circle(img,(ver_left_x,hor_up_y), 5, (0,255,0), -1)
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
		img_crop=img[hor_up_y:hor_up_y+height, ver_left_x:ver_left_x+width]
		filename="/cropped_"+os.path.basename(self._img_path)
		cropped_boundary_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(cropped_boundary_path,img_crop)
		self._last_saved_image_path = cropped_boundary_path
		if result:
			result = img_crop
		return result


#==============================================================================
	def _locatePartInHistogram(self,hist,arr_len):
		hist1=np.asarray(hist)


		#Discarding boundary region
		#Lower Boundary - Starting from beginning, if hist does not increase for 20 consecutive steps
		boundary_limit=0
		delta=0
		for i in range(0,arr_len-1,1):
			delta=hist1[i+1]-hist1[i]
			if boundary_limit<=20:
				if delta<=0:
					boundary_limit=boundary_limit+1
			else:
				lower=i
				break

		#Upper Boundary - Starting from end, if hist does not increase for 20 consecutive steps
		boundary_limit=0
		delta=0

		for i in range(arr_len-1,1,-1):
			delta=hist1[i]-hist1[i-1]
			if boundary_limit<=20:
				if delta>=0:
					boundary_limit=boundary_limit+1
			else:
				upper=i
				break


		#Replacing boundary with high intensity
		hist1[0:lower]=hist1[lower]
		hist1[upper:arr_len]=hist1[upper]

		# HIST STATISTICS
		index_min=np.argmin(hist1)
		hist_min=np.min(hist1)
		hist_max=np.max(hist1)

		# DIVIDING HIST IN TWO PARTS - (0 to min) and (min+1, end)
		hist1_part1=hist1[0:index_min+1]
		hist1_part1=hist1_part1[::-1]
		hist1_part2=hist1[index_min+2:arr_len]

		# INTERSECTION OF (Max + Min)/2, HIST PART1 AND HIST PART2
		check_value=(hist_max+hist_min)/2
		mean_intersection1=index_min-(np.abs(hist1_part1 - check_value)).argmin()
		mean_intersection2=index_min+(np.abs(hist1_part2 - check_value)).argmin()
		center=math.ceil((mean_intersection1+mean_intersection2)/2)

		return center,mean_intersection1,mean_intersection2

#==============================================================================
# _centerofMass
#==============================================================================

	def _centerofMass(self,crop_img):
		row_hist=[]
		col_hist=[]

		n_rows=crop_img.shape[0]
		n_cols=crop_img.shape[1]

		#Finding Row wise Intensity average
		for y in range(0,n_rows,1):
			row_avg=np.mean(crop_img[y,:])
			row_hist.append(row_avg)

		#Finding Column wise Intensity average
		for x in range(0,n_cols,1):
			col_avg=np.mean(crop_img[:,x])
			col_hist.append(col_avg)

		# Visualization of histogram in the picture
		"""s0 = crop_img.shape[0]
		s1 = crop_img.shape[1]
		#crop_img = cv2.resize(crop_img, (s1+int(255/2), s0+int(255/2)))
		#crop_img[crop_img.shape[0]-int(255/2):crop_img.shape[0], crop_img.shape[1]-int(255/2):crop_img.shape[1]] = 0
		x=0
		for col in col_hist:
			crop_img[crop_img.shape[0]-int(col/2):crop_img.shape[0], x] = 0
			#crop_img[crop_img.shape[0]-int(255/2), x] = 0
			x+=1

		x=0
		for row in row_hist:
			crop_img[x, crop_img.shape[1]-int(row/2):crop_img.shape[1]] = 0
			#crop_img[x, crop_img.shape[1]-int(255/2)] = 0
			x+=1
		#cv2.imshow("Histogram",crop_img)
		#cv2.waitKey(0)

		crop_img = cv2.resize(crop_img, (s1, s0))
"""

		# Find part in histogram
		cy,y1,y2=self._locatePartInHistogram(row_hist,n_rows)
		cx,x1,x2=self._locatePartInHistogram(col_hist,n_cols)

		# Generate result image and return
		cv2.circle(crop_img,(int(cx),int(cy)), 5, (0,255,0), -1)
		filename="/finalcm_"+os.path.basename(self._img_path)
		finalcm_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(finalcm_path,crop_img)
		self._last_saved_image_path = finalcm_path

		return cx,cy,x1,y1,x2,y2


# Finds lines in the given image by applying a Canny operator and a Hough transformation.
# Returns an array of lines and the estimated diameter of the object.
#==============================================================================
	def _extractLines(self, gray_img, low_threshold):
		cx,cy,x1,y1,x2,y2=self._centerofMass(gray_img)
		len_diagonal=math.sqrt(((x1-x2)**2)+((y1-y2)**2))

		#Detect Lines
		#edges = cv2.Canny(gray_img,50,150,apertureSize = 3)
		edges = cv2.Canny(gray_img,low_threshold,low_threshold*3,apertureSize = 3)
		if self._interactive: cv2.imshow("Lines orientation",edges)
		if self._interactive: cv2.waitKey(0)


		#lines = cv2.HoughLines(edges,2,np.pi/180,int(len_diagonal/4))
		lines = cv2.HoughLines(edges,1,np.pi/180,int(len_diagonal/4))
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