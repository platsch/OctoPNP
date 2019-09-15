#ifndef _COLOR_H_
#define _COLOR_H_
#include <iostream>
#include <tuple>

#ifndef OPENCV_H
#define OPENCV_H
#include "opencv2/opencv.hpp"
#endif

class Color {
  public:
    static std::vector<std::vector<int>> getHSVColorRange(const std::string& imagePath);
  private:
    static cv::Mat readColors(const cv::Mat& image) ;
};
#endif
