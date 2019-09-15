#ifndef _HOUGH_H_
#define _HOUGH_H_
#define PI 3.141592653589793238462643383279502884L

#ifndef OPENCV_H
#define OPENCV_H
#include "opencv2/opencv.hpp"
#endif

#include <chrono>
#include "image.h"

struct Rpoint {
	int dx;
	int dy;
	float phi;
};

struct Rpoint2 {
	float x;
	float y;
	int phiindex;
};

class Hough {
  public:
    static std::vector<float> matchTemplate(const cv::Mat& searchImage, const cv::Mat& templateImage, const std::vector<std::vector<int>>& colorRange, const int expectedSize);
    static cv::Mat drawCandidate(const cv::Mat& searchImage, const cv::Mat& templateImage,  const std::vector<float> candidate);
  private:
    // minimum and maximum width of scaled contour
    static int wmin;
    static int wmax;
    // minimum and maximum rotation allowed for template
    static float phimin;
    static float phimax;
    // dimension in pixels of squares in image
    static int rangeXY;
    // interval to increase scale
    static int rangeS;
    // number of intervals for angles of R-table:
    static int intervals;
    // to store the RTable
    static std::vector<std::vector<cv::Vec2i>> Rtable;
    // Points read from template
    static std::vector<Rpoint> pts;
    // The accumulator matrix
    static cv::Mat accum;
    // The maximal width of the template
    static int wtemplate;
    // The center point of the template
    static int ctemplate[2];
    // Standard image dimensions to resize the working image
    static int imageSize;
    // Debug flag
    static bool DEBUG;

    static void createRtable(const cv::Mat& templateImage);
    static void readPoints(const cv::Mat& original_img, const cv::Mat& template_img);
    static void readRtable();
    static void accumulate(const cv::Mat& searchImage);
    static std::vector<float> bestCandidate(const cv::Mat& searchImage, const cv::Vec2i& originalDimensions);

    static inline int roundToInt(float num) {
      return (num > 0.0) ? (int)(num + 0.5f) : (int)(num - 0.5f);
    }

    static inline short at4D(cv::Mat& mt, int i0, int i1, int i2, int i3){
      return *( (short*)(mt.data + i0*mt.step.p[0] + i1*mt.step.p[1] + i2*mt.step.p[2] + i3*mt.step.p[3]));
    }

    static inline short* ptrat4D(cv::Mat& mt, int i0, int i1, int i2, int i3){
      return (short*)(mt.data + i0*mt.step.p[0] + i1*mt.step.p[1] + i2*mt.step.p[2] + i3*mt.step.p[3]);
    }
};
#endif