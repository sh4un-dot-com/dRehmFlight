// Minimal stub of schema_generated.h to satisfy GetModel() and Model::version()
#ifndef TFLITE_SCHEMA_GENERATED_STUB_H
#define TFLITE_SCHEMA_GENERATED_STUB_H

// Ensure version macro is available
#include "../version.h"

namespace tflite {

struct Model {
  // Return a matching schema version for the stub
  int version() const { return TFLITE_SCHEMA_VERSION; }
};

// Assume model_data is a pointer to model bytes; return pointer to a dummy Model
inline const Model* GetModel(const unsigned char* /*model_data*/) {
  static Model m;
  return &m;
}

} // namespace tflite

#endif // TFLITE_SCHEMA_GENERATED_STUB_H
