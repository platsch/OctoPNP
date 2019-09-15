#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "../include/color.h"
#include "../include/image.h"
#include "../include/hough.h"

namespace pybind11 { namespace detail {

template <> struct type_caster<cv::Mat> {
    public:
        /**
         * This macro establishes the name 'inty' in
         * function signatures and declares a local variable
         * 'value' of type inty
         */
        PYBIND11_TYPE_CASTER(cv::Mat, _("numpy.ndarray"));

        /**
         * Conversion part 1 (Python->C++): convert a PyObject into a inty
         * instance or return false upon failure. The second argument
         * indicates whether implicit conversions should be applied.
         */
        bool load(handle src, bool)
        {
            /* Try a default converting into a Python */
            array b(src, true);
            buffer_info info = b.request();

            int ndims = info.ndim;

            decltype(CV_32F) dtype;
            size_t elemsize;
            if (info.format == format_descriptor<float>::format()) {
                if (ndims == 3) {
                    dtype = CV_32FC3;
                } else {
                    dtype = CV_32FC1;
                }
                elemsize = sizeof(float);
            } else if (info.format == format_descriptor<double>::format()) {
                if (ndims == 3) {
                    dtype = CV_64FC3;
                } else {
                    dtype = CV_64FC1;
                }
                elemsize = sizeof(double);
            } else if (info.format == format_descriptor<unsigned char>::format()) {
                if (ndims == 3) {
                    dtype = CV_8UC3;
                } else {
                    dtype = CV_8UC1;
                }
                elemsize = sizeof(unsigned char);
            } else {
                throw std::logic_error("Unsupported type");
                return false;
            }

            std::vector<int> shape = {info.shape[0], info.shape[1]};

            value = cv::Mat(cv::Size(shape[1], shape[0]), dtype, info.ptr, cv::Mat::AUTO_STEP);
            return true;
        }

        /**
         * Conversion part 2 (C++ -> Python): convert an inty instance into
         * a Python object. The second and third arguments are used to
         * indicate the return value policy and parent object (for
         * ``return_value_policy::reference_internal``) and are generally
         * ignored by implicit casters.
         */
        static handle cast(const cv::Mat &m, return_value_policy, handle defval)
        {
            std::string format = format_descriptor<unsigned char>::format();
            size_t elemsize = sizeof(unsigned char);
            int dim;
            switch(m.type()) {
                case CV_8U:
                    format = format_descriptor<unsigned char>::format();
                    elemsize = sizeof(unsigned char);
                    dim = 2;
                    break;
                case CV_8UC3:
                    format = format_descriptor<unsigned char>::format();
                    elemsize = sizeof(unsigned char);
                    dim = 3;
                    break;
                case CV_32F:
                    format = format_descriptor<float>::format();
                    elemsize = sizeof(float);
                    dim = 2;
                    break;
                case CV_64F:
                    format = format_descriptor<double>::format();
                    elemsize = sizeof(double);
                    dim = 2;
                    break;
                default:
                    throw std::logic_error("Unsupported type");
            }

            std::vector<size_t> bufferdim;
            std::vector<size_t> strides;
            if (dim == 2) {
                bufferdim = {(size_t) m.rows, (size_t) m.cols};
                strides = {elemsize * (size_t) m.cols, elemsize};
            } else if (dim == 3) {
                bufferdim = {(size_t) m.rows, (size_t) m.cols, (size_t) 3};
                strides = {(size_t) elemsize * m.cols * 3, (size_t) elemsize * 3, (size_t) elemsize};
            }
            return array(buffer_info(
                m.data,         /* Pointer to buffer */
                elemsize,       /* Size of one scalar */
                format,         /* Python struct-style format descriptor */
                dim,            /* Number of dimensions */
                bufferdim,      /* Buffer dimensions */
                strides         /* Strides (in bytes) for each index */
                )).release();
        }

    };
}} // namespace pybind11::detail

namespace py = pybind11;

//----------------------------------------------------------<
// Wrappers

static cv::Mat pyCropImageToRect(const cv::Mat& inputImage, const std::vector<int> boudingRect) {
  cv::Rect bRect;
  bRect.height = boudingRect[0];
  bRect.width = boudingRect[1];
  bRect.x = boudingRect[2];
  bRect.y = boudingRect[3];
  return Image::cropImageToRect(inputImage, bRect);
}

static std::vector<int> pyFindContainedRect(const cv::Mat& inputImage) {
  cv::Rect bRect = Image::findContainedRect(inputImage);
  return std::vector<int> {bRect.height, bRect.width, bRect.x, bRect.y};
}

//----------------------------------------------------------<
// Python module definition

void initPythonBindings(py::module& m) {

  m.def("getHSVColorRange", &Color::getHSVColorRange,
    "Returns lower and upper color ranges from provided background picture.",
    py::arg("imagePath"));

  m.def("matchTemplate", &Hough::matchTemplate,
    "Detects and retrieves most orientation of provided template in search image.",
    py::arg("imagePath"),
    py::arg("templatePath"),
    py::arg("colorRange"),
    py::arg("expectedSize")=-1);

  m.def("drawCandidate", &Hough::drawCandidate,
    "Draws and returns supplied candidate based on search and template image.",
    py::arg("searchImage"),
    py::arg("templateImage"),
    py::arg("candidate"));

  m.def("findShape",
    py::overload_cast<const cv::Mat&>(&Image::findShape),
    "Detects arbitrary shape in provided search image.",
    py::arg("inputImage"));

  m.def("findShape",
    py::overload_cast<const std::string&>(&Image::findShape),
    "Detects arbitrary shape in provided search image.",
    py::arg("imagePath"));

  m.def("removeColorRange", &Image::removeColorRange,
    "Removes provided HSV color range from picture",
    py::arg("inputImage"),
    py::arg("colorRange"));

  m.def("binaryFromRange", &Image::binaryFromRange,
    "Creates binary image based on provided color range",
    py::arg("inputImage"),
    py::arg("colorRange"));

  m.def("cropImageToMask", &Image::cropImageToMask,
    "Crops image to innersize of biggest contour in provided binary mask.",
    py::arg("inputImage"),
    py::arg("mask"));

  m.def("createColorRangeMask", &Image::createColorRangeMask,
    "Creates binary mask only containing elements contained in provided color range.",
    py::arg("inputImage"),
    py::arg("colorRange"));

  m.def("findContainedRect", &pyFindContainedRect,
    "Extracts bouding rect from shape contained in mask.",
    py::arg("mask"));

  m.def("cropImageToRect", &pyCropImageToRect,
    "Crops image to bounding rect.",
    py::arg("inputImage"),
    py::arg("boundingRect"));
}

// pybind11 legacy fallback
#ifndef PYBIND11_MODULE
PYBIND11_PLUGIN(VisionPNP) {
  py::module m("VisionPNP", "python plugin for cv pick and place automation");
  initPythonBindings(m);
  return m.ptr();
}
#else
PYBIND11_MODULE(VisionPNP, m) {
  m.doc() = "python plugin for cv pick and place automation";
  initPythonBindings(m);
}
#endif
