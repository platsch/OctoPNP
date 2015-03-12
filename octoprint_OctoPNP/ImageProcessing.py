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
#from matplotlib import pyplot as plt

class ImageProcessing:

	def __init__(self, box_size):
		self.box_size=box_size
		self._img_path = ""

	def get_displacement(self,img_path):

		self._img_path = img_path
		print "Inside get_displacement"
		# open image file
		img=cv2.imread(img_path,cv2.IMREAD_COLOR)
		# make a copy of the file for later inspection

		#DETECT BOUNDARY AND CROP
		crop_image=self._boundaryDetect(img)

		#GET CENTER OF MASS
		gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
		cmx,cmy=self.centerofMass(gray_img)

		#RETURN DISPLACEMENT
		print "Calculating Displacement..."
		print "shape of cropped image",np.shape(crop_image)
		n_rows=crop_image.shape[0]
		n_cols=crop_image.shape[1]
		displacement_x=(cmx-n_rows/2)*self.box_size/n_rows
		displacement_y=((n_cols-cmy)-n_cols/2)*self.box_size/n_cols

		return displacement_x,displacement_y

	def _boundaryDetect(self,img):
		print "Inside _boundaryDetect"
		img_bkp=img.copy()
		# Converting Colorspace : BGR to HSV
		hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

		# Extracting Green Channel
		green = np.uint8([[[0,255,0 ]]])
		hsv_green = cv2.cvtColor(green,cv2.COLOR_BGR2HSV)
		lower_green=np.array([hsv_green[0][0][0]-40,100,100])
		upper_green=np.array([hsv_green[0][0][0]+40,255,255])

		# Threshold the HSV image to get only green colors
		mask = cv2.inRange(hsv, lower_green, upper_green)

		# Bitwise-AND mask and original image
		res = cv2.bitwise_and(img,img, mask= mask)
		#Show Images
#		cv2.imshow('Green Channel',res)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()


		#Find Lines
		# Converting Image to Gray Scale
		gray_img=cv2.cvtColor(cv2.cvtColor(res,cv2.COLOR_HSV2BGR),cv2.COLOR_BGR2GRAY)

		# Smoothing Image
		gray_img = cv2.GaussianBlur(gray_img, (25, 25), 0)

		# Invert Image
		ret,thresh = cv2.threshold(gray_img,0,255,cv2.THRESH_BINARY_INV)
#		cv2.imshow('Inverted',thresh)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()

		# Finding Contours with Max Area
		contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
		print "number of contours detected", len(contours)

		cnt=0
		maxArea=0
		flag=0
		maxArea=0
		for i in contours:
			currArea=cv2.contourArea(i)
			if currArea > 0.0:
				if currArea>maxArea:
					maxArea=currArea
					flag=cnt
			cnt=cnt+1

		# Drawing the contour and the bounding rectangle
		cv2.drawContours(img, contours, flag, (0,0,255), 3)
		x,y,w,h = cv2.boundingRect(contours[flag])

		cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)

		print "rectangle width",w
		print "rectangle height",h
		# Show Image
#		cv2.imshow("Contours",img)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()
		#img1=img
		img_crop=img_bkp[x:x+w-1,y:y+h-1]
		filename="/cropped_"+os.path.basename(self._img_path)
		cropped_boundary_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(cropped_boundary_path,img_crop)
		return img_crop

#==============================================================================
# Center of Array - Generalized
#==============================================================================

	def _center_of_array(self,hist,arr_len):
		print "Inside _center_of_array"
		hist1=np.asarray(hist)
		boundary_limit=0
		delta=0

		#Discarding boundary region
		print "Discarding boundary region"

		#Lower Boundary - Starting from beginning, if hist does not increase for 20 consecutive steps
		for i in range(0,arr_len-1,1):
			delta=hist1[i+1]-hist1[i]
			if boundary_limit<=20:
				if delta<=0:
					boundary_limit=boundary_limit+1
			else:
				lower=i
				break

		print "Lower boundary:",lower

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

		print "Upper boundary:",upper

		#REPLACING BOUNDARY WITH HIGH INTENSITY

		hist1[0:lower]=hist1[lower]
		hist1[upper:arr_len]=hist1[upper]

		#Plotting boundary processed hist
		#len_idx=np.asanyarray(range(0,arr_len,1))
		#plt.plot(len_idx,hist1,color='green')


		# HIST STATISTICS
		index_min=np.argmin(hist1)
		hist_min=np.min(hist1)
		hist_max=np.max(hist1)

		print "Histogram Statistics"
		print "===================="
		print "Hist Minimum Index",index_min
		print "Hist Minimum value:",hist1[index_min],hist_min
		print "Hist Maximum value:",hist_max

		# INTERSECTION OF (Max + Min)/2 AND HIST


		# DIVIDING HIST IN TWO PARTS - (0 to min) and (min+1, end)
		hist1_part1=hist1[0:index_min+1]
		hist1_part1=hist1_part1[::-1]
		hist1_part2=hist1[index_min+2:arr_len]

		check_value=(hist_max+hist_min)/2
		print "CHECK VALUE:",check_value

		mean_intersection1=index_min-(np.abs(hist1_part1 - check_value)).argmin()
		mean_intersection2=index_min+(np.abs(hist1_part2 - check_value)).argmin()

		print "Intersection of Mean and Row_Hist"
		print mean_intersection1, mean_intersection2

		center=math.ceil((mean_intersection1+mean_intersection2)/2)
		return center,mean_intersection1,mean_intersection2

	def _centerofMass(self,crop_img):
		print "Inside _centerofMass"
		row_hist=[]
		col_hist=[]

		print np.shape(crop_img)
		n_rows=crop_img.shape[0]
		n_cols=crop_img.shape[1]

		print "n_rows,n_cols:",n_rows,n_cols

		#Finding Row wise Intensity average
		for y in range(0,n_rows,1):
			row_avg=np.mean(crop_img[y,:])
			row_hist.append(row_avg)

		#Finding Column wise Intensity average
		for x in range(0,n_cols,1):
			col_avg=np.mean(crop_img[:,x])
			col_hist.append(col_avg)


		#Plotting row and column histogram
		#len_id_row=np.asanyarray(range(0,n_rows,1))
		#len_id_col=np.asanyarray(range(0,n_cols,1))
		#plt.plot(len_id_row,row_hist,color='red')
		#plt.plot(len_id_col,col_hist,color='blue')

		#Calling Center Of Array for row_hist and col_hist
		print "Calling Center of Array for row_hist"
		cy,y1,y2=self._center_of_array(row_hist,n_rows)

		print "Calling Center of Array for col_hist"
		cx,x1,x2=self._center_of_array(col_hist,n_cols)

		cv2.circle(crop_img,(int(cx),int(cy)), 5, (0,255,0), -1)
		filename="/finalcm_"+os.path.basename(self._img_path)
		finalcm_path=os.path.dirname(self._img_path)+filename
		cv2.imwrite(finalcm_path,crop_img)

		print "Center(X,Y):",cx,cy

		return cx,cy,x1,y1,x2,y2


	def centerofMass(self,crop_img):
		print "Inside centerofMass"
		cx,cy,x1,y1,x2,y2=self._centerofMass(crop_img)
		return cx,cy

	def _get_lendiagonal(self,img):
		print "Inside _get_lendiagonal"
		cx,cy,x1,y1,x2,y2=self._centerofMass(img)
		len_diagonal=math.sqrt(((x1-x2)**2)+((y1-y2)**2))
		print "Length of Diagonal:",len_diagonal
		return len_diagonal

	def get_orientation(self,img):
		print "Inside get_orientation"
		gray_img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		len_diagonal=self._get_lendiagonal(gray_img)

		#Detect Lines
		edges = cv2.Canny(gray_img,50,150,apertureSize = 3)
		lines = cv2.HoughLines(edges,1,np.pi/180,int(len_diagonal/4))
		arr_theta=[]

		#drawing the lines and storing theta in degree for future calculation
		if len(lines[0])==0:
			print "..........NO LINE DETECTED......."
			avg_deviation=0
		else:

			for rho,theta in lines[0]:
				theta_degree=(180/math.pi)*theta
				if theta_degree>90:
					arr_theta.append(90+(180-theta_degree))
				elif theta_degree<=90:
					arr_theta.append(90-theta_degree)

				a = np.cos(theta)
				b = np.sin(theta)
				x0 = a*rho
				y0 = b*rho
				x1 = int(x0 + 1000*(-b))
				y1 = int(y0 + 1000*(a))
				x2 = int(x0 - 1000*(-b))
				y2 = int(y0 - 1000*(a))
				cv2.line(gray_img,(x1,y1),(x2,y2),(0,255,0),2)


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

			print "Theta:",arr_theta
			print "Deviation:",arr_deviation

		return avg_deviation
