#include "../include/color.h"

std::vector<std::vector<int>> Color::getHSVColorRange(const std::string& imagePath) {
  std::vector<std::vector<int>> threshold;
  cv::Mat inputImage = cv::imread(imagePath);
  cv::Mat workingCopy = inputImage.clone();
  cv::Mat colorMatrix;

  // Convert to HSV spectrum and read smoothed colors from image
  cv::cvtColor(workingCopy, workingCopy, cv::COLOR_BGR2HSV);
  cv::blur(workingCopy, workingCopy, cv::Size( 8, 8 ));
  colorMatrix = readColors(workingCopy);

  // Calculates mean and standard deviation of all color elements.
  cv::Scalar mean,dev;
  cv::meanStdDev(colorMatrix,mean,dev);
  threshold.push_back(std::vector<int> {int(mean[0]-dev[0]*4), int(mean[1]-dev[1]*4), int(mean[2]-dev[2]*4)});
  threshold.push_back(std::vector<int> {int(mean[0]+dev[0]*4), int(mean[1]+dev[1]*4), int(mean[2]+dev[2]*4)});

  return threshold;
}

cv::Mat Color::readColors(const cv::Mat& image) {
  cv::Mat colors;
  int offset = 50;
  int cX = (image.cols/2)-offset;
  int cY = (image.rows/2)-offset;

  for (int x=0; x<image.cols; x++) {
    for (int y=0; y<image.rows; y++) {
      if ((x < cX || x > cX + offset*2) && (y < cY || y > cY + offset*2 )) {
        cv::Vec3b p = image.at<cv::Vec3b>(y, x);
        colors.push_back(p);
      }
    }
  }
  return colors;
}
