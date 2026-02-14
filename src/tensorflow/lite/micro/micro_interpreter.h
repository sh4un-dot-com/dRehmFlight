// Minimal stub for MicroInterpreter-related types used in the sketch
#ifndef TFLITE_MICRO_INTERPRETER_STUB_H
#define TFLITE_MICRO_INTERPRETER_STUB_H

#include <cstring>
#include <cstdint>

// Simple TfLiteTensor stub matching accesses used in the sketch
typedef struct TfLiteTensor {
  struct Dims { int* data; };
  struct Dims* dims;
  union { float* f; } data;
} TfLiteTensor;

// status code
enum { kTfLiteOk = 0 };

namespace tflite {
  // forward declarations to avoid ordering issues
  class AllOpsResolver;
  struct Model;

class MicroInterpreter {
public:
  // Accept a generic model pointer to avoid strict type dependency on stub Model
  MicroInterpreter(const void* /*model*/, const AllOpsResolver& /*resolver*/, uint8_t* /*arena*/, int /*arena_size*/, void* /*er*/) {
    // create simple internal tensors
    // simple dims: [1,8]
    static int in_dims_data[2] = {1, 8};
    static int out_dims_data[2] = {1, 1};
    // allocate static arrays
    static float in_data[8];
    static float out_data[1];
    std::memset(in_data, 0, sizeof(in_data));
    std::memset(out_data, 0, sizeof(out_data));
    input_tensor_.dims = &in_dims_storage_;
    in_dims_storage_.data = in_dims_data;
    output_tensor_.dims = &out_dims_storage_;
    out_dims_storage_.data = out_dims_data;
    input_tensor_.data.f = in_data;
    output_tensor_.data.f = out_data;
  }

  int AllocateTensors() { return kTfLiteOk; }
  TfLiteTensor* input(int /*i*/) { return &input_tensor_; }
  TfLiteTensor* output(int /*i*/) { return &output_tensor_; }
  int Invoke() { output_tensor_.data.f[0] = 0.0f; return kTfLiteOk; }

private:
  TfLiteTensor input_tensor_;
  TfLiteTensor output_tensor_;
  TfLiteTensor::Dims in_dims_storage_;
  TfLiteTensor::Dims out_dims_storage_;
};

} // namespace tflite

#endif // TFLITE_MICRO_INTERPRETER_STUB_H
