# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 15:54:46 2015

@author: soubarna
"""

import cv2
import numpy as np
#import scipy.signal as sig
from matplotlib import pyplot as plt


def boundary_detect(img):
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
    cv2.imshow('Green Channel',res)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

           
    #Find Lines
    
    # Converting Image to Gray Scale
    gray_img=cv2.cvtColor(cv2.cvtColor(res,cv2.COLOR_HSV2BGR),cv2.COLOR_BGR2GRAY)
    
    # Smoothing Image
    gray_img = cv2.GaussianBlur(gray_img, (15, 15), 0)
    
    # Invert Image 
    ret,thresh = cv2.threshold(gray_img,0,255,cv2.THRESH_BINARY_INV)
    cv2.imshow('Inverted',thresh)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

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
    cv2.imshow("Contours",img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    #img1=img
    img_crop=img_bkp[x:x+w-1,y:y+h-1]
    #cv2.imwrite("cropped_output.jpg",img1)
    return img_crop

def center_of_mass(img):
    img_bkp=img.copy()
    
    # Plotting histogram
    #plt.hist(img.ravel(),256,[0,256])
    #plt.show()
    
    # Finding contours
    ret,thresh = cv2.threshold(img,50,255,cv2.THRESH_BINARY_INV)
    cv2.imshow("threshold",thresh)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    
    contours, hierarchy = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    print "number of contours", len(contours)

    # Finding the contour with the max area
    cnt=0
    maxArea=0
    flag=0
    
    for i in contours:
        currArea=cv2.contourArea(i)
        if currArea > 0.0:
            
            if currArea>maxArea:
                maxArea=currArea
                flag=cnt
        cnt=cnt+1
    #==============================================================================
    # Calculating center of mass for the max area 
    #==============================================================================
    M = cv2.moments(contours[flag])
    cx1 = int(M['m10']/M['m00'])
    cy1 = int(M['m01']/M['m00'])
    cv2.circle(img_bkp,(cx1,cy1), 5, (255,0,0), -1)
    cv2.drawContours(img_bkp, contours, -1, (0,255,0), 3)
    
    cv2.imshow("Contours",img_bkp)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print "Center of Mass : ",cx1,cy1
    return cx1,cy1

def center_of_mass2(img):
    row_hist=[]
    col_hist=[]
    print np.shape(img)
    n_rows=img.shape[0]
    n_cols=img.shape[1]
    
    print n_rows, n_cols
    
    #Finding Column wise Intensity average
    for x in range(0,n_rows-1,1):
        col_avg=np.mean(img[x])
        col_hist.append(col_avg)
        
    #Finding Row wise Intensity average  
    for y in range(0,n_cols-1,1):
        row_avg=np.mean(img[:,y])
        row_hist.append(row_avg)
    
    #Plotting row and column histogram
    row_len=np.asanyarray(range(0,n_cols-1,1))
    col_len=np.asanyarray(range(0,n_rows-1,1))
    plt.plot(row_len,row_hist,color='red')  
    plt.plot(col_len,col_hist,color='blue')  
    
    
    #=============================================================================
    #APPROACH1
    #=============================================================================
    
    #Row hist statistics
    row_hist_mean=np.mean(row_hist)
    row_hist_min=np.min(row_hist)
    row_hist_std=np.std(row_hist)
    print "Row_hist details:", row_hist_mean, row_hist_std

    #Row hist statistics
    col_hist_mean=np.mean(col_hist)
    col_hist_min=np.min(col_hist)
    col_hist_std=np.std(col_hist)
    print "Col_hist details:", col_hist_mean, col_hist_std
    
    row_hist1=np.asarray(row_hist)
    col_hist1=np.asarray(col_hist)
    
    #Extracting the valley in the histogram for Row
    mask1 = cv2.inRange(row_hist1, row_hist_mean-row_hist_std, row_hist_mean+row_hist_std)
    res1 = cv2.bitwise_and(row_hist1,row_hist1, mask= mask1)

    #Extracting the valley in the histogram for Column
    mask2 = cv2.inRange(col_hist1, col_hist_mean-col_hist_std, col_hist_mean+col_hist_std)
    res2 = cv2.bitwise_and(col_hist1,col_hist1, mask= mask2)
    
    xindex_list=[]
    for i in range(len(res1)):
        if res1[i]>0:
            xindex_list.append(i)

    yindex_list=[]
    for i in range(len(res2)):
        if res2[i]>0:
            yindex_list.append(i)
            
    xindex_arr=np.asarray(xindex_list)
    yindex_arr=np.asarray(yindex_list)
    row_median=np.median(xindex_arr)
    col_median=np.median(yindex_arr)
    

    
    plt.show()  

    #=============================================================================
    #APPROACH2
    #=============================================================================
    print "Approach2 -"
    print "Finding row minimum"
    
    lxmin=int(len(row_hist)/2)
    rxmin=int(len(row_hist)/2)  
    lxcnt=0
    rxcnt=0
    lxvalue=row_hist[lxmin]
    rxvalue=row_hist[rxmin]
    
    for i in range(int(len(row_hist)/2),0,-1):
        
        if lxcnt<=10:
            if row_hist[i-1]-row_hist[i]>0:
                lxcnt=lxcnt+1
            else:
                lxmin=i-1
                lxvalue=row_hist[lxmin]
            
    for i in range(int(len(row_hist)/2),len(row_hist),1):
        
        if rxcnt<=10:
            if row_hist[i+1]-row_hist[i]>0:
                rxcnt=rxcnt+1
            else:
                rxmin=i+1
                rxvalue=row_hist[rxmin]
    
    if lxvalue>rxvalue:
        row_min=rxmin
    else:
        row_min=lxmin
        
    print "lxmin,rxmin,row_min:", lxvalue,rxvalue,row_min
    
    print "Finding column minimum"
    lymin=int(len(col_hist)/2)
    rymin=int(len(col_hist)/2)
    lycnt=0
    rycnt=0    
    lyvalue=row_hist[lxmin]
    ryvalue=row_hist[rxmin]
    
    for i in range(int(len(col_hist)/2),0,-1):
        
        if lycnt<=10:
            if col_hist[i-1]-col_hist[i]>0:
                lycnt=lycnt+1
            else:
                lymin=i-1
                lyvalue=col_hist[lymin]

            
    for i in range(int(len(col_hist)/2),len(col_hist),1):
        
        if rycnt<=10:
            if col_hist[i+1]-col_hist[i]>0:
                rycnt=rycnt+1
            else:
                rymin=i+1
                ryvalue=col_hist[rymin]
     
    if lyvalue>ryvalue:
        col_min=rymin
    else:
        col_min=lymin
        
        
    print "lymin,rymin,col_min:",lyvalue,ryvalue,col_min
    
    print "approach 1: row median", row_median
    print "approach2: row min:",row_min           
    print "approach2: col min:",col_min 
    
    return row_min, col_min
    
def center_of_mass3(img):
    row_hist=[]
    col_hist=[]
    print np.shape(img)
    n_rows=img.shape[0]
    n_cols=img.shape[1]
    
    print n_rows, n_cols
    
    #Finding Column wise Intensity average
    for x in range(0,n_rows-1,1):
        col_avg=np.mean(img[x])
        col_hist.append(col_avg)
        
    #Finding Row wise Intensity average  
    for y in range(0,n_cols-1,1):
        row_avg=np.mean(img[:,y])
        row_hist.append(row_avg)
    
    #Plotting row and column histogram
    row_len=np.asanyarray(range(0,n_cols-1,1))
    col_len=np.asanyarray(range(0,n_rows-1,1))
    plt.plot(row_len,row_hist,color='red')  
    plt.plot(col_len,col_hist,color='blue')  

    #Row hist statistics
    row_hist_mean=np.mean(row_hist)
    row_hist_min=np.min(row_hist)
    row_hist_std=np.std(row_hist)
    print "Row_hist details:", row_hist_mean, row_hist_std

    #Row hist statistics
    col_hist_mean=np.mean(col_hist)
#    col_hist_min=np.min(col_hist)
    col_hist_std=np.std(col_hist)
    print "Col_hist details:", col_hist_mean, col_hist_std
    
    row_hist1=np.asarray(row_hist)
    col_hist1=np.asarray(col_hist)
        
    row_boundary_limit=0
    col_boundary_limit=0
    delta=0
    
    for i in range(0,n_rows-1,1):
        delta=row_hist1[i+1]-row_hist1[i]
        if row_boundary_limit<=10:
            if delta<=0:
                row_boundary_limit=row_boundary_limit+1
        else:
            row_lower=i
            break
        
    #row_lower=i

    delta=0     
    row_boundary_limit=0
    
    for i in range(n_rows-1,1,-1):
        print i
        delta=row_hist1[i]-row_hist1[i-1]
        if row_boundary_limit<=10:
            if delta<=0:
                row_boundary_limit=row_boundary_limit+1
            else:
                row_upper=i
                break
   
    print "for row_hist boundary, limits:",row_lower,row_upper

    for x in range(0,row_lower-1,1):  
        if row_hist1[x]<row_hist_mean:
            row_hist1[x]=255

    for x in range(row_upper-1,1):  
        if row_hist1[x]<row_hist_mean:
            row_hist1[x]=255
        
    delta=0
    for j in range(0,n_rows-1,1):
        delta=col_hist1[i+1]-col_hist1[i]
        if col_boundary_limit<=10:
            if delta<=0:
                col_boundary_limit=col_boundary_limit+1
        else:
            break
            
            
    print "for col_hist boundary, lower limit:",j

    for y in range(0,j-1,1):  
        if col_hist1[y]<col_hist_mean:
            col_hist1[y]=255

    
# Loading Image in Color mode
comp_img=cv2.imread("../Component3.tiff",cv2.IMREAD_COLOR)

# Detecting Border
crop_image=boundary_detect(comp_img)
cv2.imshow("Cropped Image",crop_image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Converting image to gray scale for center of mass
gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
print "Invoking center of mass"
cx1,cy1=center_of_mass(gray_img)
gray_img_bkp=gray_img.copy()
#cx2,cy2=center_of_mass2(gray_img_bkp)
center_of_mass3(gray_img_bkp)
print cx1,cy1
   
cv2.circle(crop_image,(cx1,cy1), 5, (255,0,0), -1)
#cv2.circle(crop_image,(int(cx2),int(cy2)), 5, (0,255,0), -1)
cv2.imshow("Final",crop_image)
cv2.waitKey(0)   
cv2.destroyAllWindows()
