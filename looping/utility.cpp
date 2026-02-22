#include <portaudio.h>
#include <cmath>
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;


static uint16_t read_u16_le(const uint8_t* p) {
    return static_cast<uint16_t>(p[0] | (static_cast<uint16_t>(p[1]) << 8));
}
static uint32_t read_u32_le(const uint8_t* p) {
    return static_cast<uint32_t>(p[0] |
                                 (static_cast<uint32_t>(p[1]) << 8) |
                                 (static_cast<uint32_t>(p[2]) << 16) |
                                 (static_cast<uint32_t>(p[3]) << 24));
}
static float clampf(float x, float lo, float hi) { return std::max(lo, std::min(hi, x)); }

// Equal-power crossfade (prevents dip in perceived loudness)
static float xfade_a(float t01) { // fade-out gain
    // cos curve: t=0 => 1, t=1 => 0
    return std::cos(0.5f * 3.14159265358979323846f * t01);
}

static float xfade_b(float t01) { // fade-in gain
    // sin curve: t=0 => 0, t=1 => 1
    return std::sin(0.5f * 3.14159265358979323846f * t01);
}