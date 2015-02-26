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

	def __init__(self,img_path,box_size):
		print "IP: ",img_path
		self.img_path = img_path
		self.box_size=box_size

	def get_cm(self):
		# open image file
		img=cv2.imread(self.img_path,cv2.IMREAD_COLOR)

		# make a copy of the file for later inspection
		shutil.copyfile(self.img_path, '/home/wasserfall/OctoPNP.tiff')

		#detect boundary and crop
		crop_image=self.boundaryDetect(img)
		#Get the center of mass
		gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
		cmx,cmy=self.centerofMass(gray_img)
		#return the displacement
		print "Calculating Displacement..."
		print "shape of cropped image",np.shape(crop_image)
		n_rows=crop_image.shape[0]
		n_cols=crop_image.shape[1]
		displacement_x=(cmx-n_rows/2)*self.box_size/n_rows
		displacement_y=((n_cols-cmy)-n_cols/2)*self.box_size/n_cols
		
		#cmx=200
		#cmy=200
		return displacement_x,displacement_y
	
	def boundaryDetect(self,img):
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
		gray_img = cv2.GaussianBlur(gray_img, (15, 15), 0)
		
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
		filename="/cropped_"+os.path.basename(self.img_path)
		cropped_boundary_path=os.path.dirname(self.img_path)+filename
		cv2.imwrite(cropped_boundary_path,img_crop)
		return img_crop

#==============================================================================
# Center of Array - Generalized
#==============================================================================

	def center_of_array(self,hist,arr_len):
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
		hist1_part1=hist1[0:index_min]
		hist1_part1=hist1_part1[::-1]
		hist1_part2=hist1[index_min+1:arr_len]
		
		check_value=(hist_max+hist_min)/2
		print "CHECK VALUE:",check_value
			
		mean_intersection1=index_min-(np.abs(hist1_part1 - check_value)).argmin()
		mean_intersection2=index_min+(np.abs(hist1_part2 - check_value)).argmin()
		
		print "Intersection of Mean and Row_Hist"
		print mean_intersection1, mean_intersection2
		
		center=math.ceil((mean_intersection1+mean_intersection2)/2)
		return center



	
	def centerofMass(self,crop_img):
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
		len_id_row=np.asanyarray(range(0,n_rows,1))
		len_id_col=np.asanyarray(range(0,n_cols,1))
		#plt.plot(len_id_row,row_hist,color='red')
		#plt.plot(len_id_col,col_hist,color='blue')
		
		#Calling Center Of Array for row_hist and col_hist
		print "Calling Center of Array for row_hist"
		cx=self.center_of_array(row_hist,n_rows)
		print "Row Center:",cx
		print "Calling Center of Array for col_hist"	
		cy=self.center_of_array(col_hist,n_cols)	
		print "Col Center:",cy
		cv2.circle(crop_img,(int(cy),int(cx)), 5, (0,255,0), -1)
		filename="/finalcm_"+os.path.basename(self.img_path)
		finalcm_path=os.path.dirname(self.img_path)+filename
		cv2.imwrite(finalcm_path,crop_img)
		return cx,cy

		
