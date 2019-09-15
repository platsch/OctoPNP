#include "../include/image.h"

//--------------------------------------------------------<
// Find shape in image and return position
std::vector<int> Image::findShape(const cv::Mat& image) {
  bool DEBUG = false;
  cv::Mat grayImage, blurImage, thresholdImage, kernel, openImage, closedImage, cannyImage;
  std::vector<std::vector<cv::Point>> contours;
  std::vector<cv::Point> hull;
  std::vector<cv::Vec4i> hierarchy;
  std::vector<int> center;

  // Create threshold image
  if(image.type() > 6) { // More than one channel
    cv::cvtColor(image, grayImage, cv::COLOR_BGR2GRAY);
  } else {
    grayImage = image.clone();
  }

  cv::blur(grayImage, blurImage, cv::Size(5, 5));
  cv::threshold(blurImage, thresholdImage, 0, 255, cv::THRESH_BINARY | cv::THRESH_OTSU);

  // Use morphology to clean the image
  kernel = cv::Mat::ones( 16, 16, CV_32F );
  cv::morphologyEx( thresholdImage, openImage, cv::MORPH_OPEN, kernel );
  cv::morphologyEx( openImage, closedImage, cv::MORPH_CLOSE, kernel );

  // Detect edges using canny edge detector
  cv::Canny( closedImage, cannyImage, 0, 1, 3 );

  // find contours
  cv::findContours(cannyImage, contours, hierarchy, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE, cv::Point(0, 0));

  // Find biggest contour
  sort(contours.begin(), contours.end(), compareContourAreas);
  std::vector<cv::Point> cnt = contours[contours.size()-1];
  std::vector<std::vector<cv::Point>> dummyVector;
  dummyVector.push_back(cnt);

  // Get the convex hull and center
  hull = getHullFromContour(cnt);
  center = getCenterOfHull(cnt);

  std::vector<std::vector<cv::Point>> dummyVectorHull;
  dummyVectorHull.push_back(hull);

  if(DEBUG) {
    // Draw contours for debugging
    drawContours(contours, hierarchy, image, "./DEBUG_findShape_contours_01.png");
    drawContours(dummyVector, hierarchy, image, "./DEBUG_findShape_contours_02.png");
    drawContours(dummyVectorHull, hierarchy, image, "./DEBUG_findShape_contours_03.png");
  }

  return center;
}

std::vector<int> Image::findShape(const std::string& pathToImage) {
  const cv::Mat image = cv::imread(pathToImage);
  return findShape(image);
}

//--------------------------------------------------------<
// Utility methods

// Replaces all areas within the provided color range with white
cv::Mat Image::removeColorRange(const cv::Mat& inputImage, const std::vector<std::vector<int>>& colorRange) {
  cv::Mat workingCopy = inputImage.clone();
  cv::Mat imageHSV;
  cv::Mat mask;

  // apply retrived color range on image
  cv::cvtColor(inputImage, imageHSV, cv::COLOR_BGR2HSV);
  cv::inRange(imageHSV, colorRange[0], colorRange[1], mask);
  workingCopy.setTo(cv::Scalar(255,255,255), mask);

  return workingCopy;
}

// Binarizes image based on color range
cv::Mat Image::binaryFromRange(const cv::Mat& inputImage, const std::vector<std::vector<int>>& colorRange) {
  cv::Mat imageHSV;
  cv::Mat mask;
  cv::Mat binarizedImage = cv::Mat::zeros(inputImage.rows, inputImage.cols, CV_8UC1);

  // apply retrived color range on image
  cv::cvtColor(inputImage, imageHSV, cv::COLOR_BGR2HSV);
  cv::inRange(imageHSV, colorRange[0], colorRange[1], mask);

  binarizedImage.setTo(255, mask);

  // Use morphology to clean the image
  cv::Mat kernel = cv::Mat::ones( 8, 8, CV_32F );
  cv::morphologyEx( binarizedImage, binarizedImage, cv::MORPH_OPEN, kernel );
  cv::morphologyEx( binarizedImage, binarizedImage, cv::MORPH_CLOSE, kernel );
  cv::blur(binarizedImage, binarizedImage, cv::Size(6,6));

  return binarizedImage;
}

// Extracts areas within the provided color range and returns binarized mask containing these areas
cv::Mat Image::createColorRangeMask(const cv::Mat& image, const std::vector<std::vector<int>>& colorRange) {
  cv::Mat blurImage, imageHSV, mask;
  cv::cvtColor(image, imageHSV, cv::COLOR_BGR2HSV);
  cv::blur(imageHSV, blurImage, cv::Size(3, 3));
  cv::inRange(imageHSV, colorRange[0], colorRange[1], mask);
  mask =  cv::Scalar::all(255) - mask;
  return mask;
}

// Create and return a convex hull based on the biggest contour provided
std::vector<cv::Point> Image::getHullFromContour(const std::vector<cv::Point>& cnt) {
  std::vector<cv::Point> hull;
  cv::convexHull(cv::Mat(cnt), hull, false);
  return hull;
}

// Return the center of a provided convex hull
std::vector<int> Image::getCenterOfHull(const std::vector<cv::Point>& hull) {
  cv::Moments m;

  m = cv::moments(hull,true);
  std::vector<int> hullCenter{int(m.m10/m.m00), int(m.m01/m.m00)};
  return hullCenter;
}

// Crop and return image based on provided mask
cv::Mat Image::cropImageToMask(const cv::Mat& image, const cv::Mat& mask) {
  cv::Rect boundRect = findContainedRect(mask);
  return image(boundRect).clone();
}

// Extract bounding rect from picture
cv::Rect Image::findContainedRect(const cv::Mat& mask) {
  cv::Rect boundRect;
  std::vector<std::vector<cv::Point>> contours;
  std::vector<cv::Vec4i> hierarchy;
  std::vector<cv::Point> cnt;

  cv::findContours(mask, contours, hierarchy, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE, cv::Point(0, 0));
  sort(contours.begin(), contours.end(), compareContourAreas);
  cnt = contours[contours.size()-1];

  boundRect = cv::boundingRect( cv::Mat(cnt) );

  return boundRect;
}

// Crop image to bouding
cv::Mat Image::cropImageToRect(const cv::Mat& image, const cv::Rect& boundRect) {
  return image(boundRect).clone();
}

// Sort contours by size
bool Image::compareContourAreas (std::vector<cv::Point> contour1, std::vector<cv::Point> contour2) {
  double i = fabs(cv::contourArea(cv::Mat(contour1)));
  double j = fabs(cv::contourArea(cv::Mat(contour2)));
  return ( i < j );
}

// Draw contours on image
void Image::drawContours(std::vector<std::vector<cv::Point>> contours, std::vector<cv::Vec4i> hierarchy, cv::Mat inputImage, std::string outputPath) {
  cv::Mat outputImage = inputImage.clone();
  cv::Scalar color = cv::Scalar( 0, 0, 255 );
  for( int i = 0; i< contours.size(); i++ ) {
    cv::drawContours( outputImage, contours, i, color, 2, 8, std::vector<cv::Vec4i>(), 0, cv::Point() );
  }
  cv::imwrite(outputPath, outputImage);
}

std::string Image::getMatType(int type) {
  std::string r;

  uchar depth = type & CV_MAT_DEPTH_MASK;
  uchar chans = 1 + (type >> CV_CN_SHIFT);

  switch ( depth ) {
    case CV_8U:  r = "8U"; break;
    case CV_8S:  r = "8S"; break;
    case CV_16U: r = "16U"; break;
    case CV_16S: r = "16S"; break;
    case CV_32S: r = "32S"; break;
    case CV_32F: r = "32F"; break;
    case CV_64F: r = "64F"; break;
    default:     r = "User"; break;
  }

  r += "C";
  r += (chans+'0');

  return r;
}
