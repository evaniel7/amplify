#include <portaudio.h>
#include "sample_voice.cpp"
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


enum class Interp { Linear, Cubic };

// Catmull-Rom cubic interpolation
static float interp_cubic(float y0, float y1, float y2, float y3, float t) {
    // y(t) = 0.5 * (2y1 + (-y0+y2)t + (2y0-5y1+4y2-y3)t^2 + (-y0+3y1-3y2+y3)t^3)
    float t2 = t*t;
    float t3 = t2*t;
    return 0.5f * (2.0f*y1 +
                   (-y0 + y2)*t +
                   (2.0f*y0 - 5.0f*y1 + 4.0f*y2 - y3)*t2 +
                   (-y0 + 3.0f*y1 - 3.0f*y2 + y3)*t3);
}

static float sample_at(const AudioBuffer& b, double framePos, int ch, Interp interp) {
    const size_t N = b.frames();
    if (N == 0) return 0.0f;

    // Clamp to valid range; looping logic handled elsewhere
    framePos = std::max(0.0, std::min(framePos, static_cast<double>(N - 1)));

    size_t i1 = static_cast<size_t>(framePos);
    double frac = framePos - static_cast<double>(i1);

    if (interp == Interp::Linear) {
        size_t i2 = std::min(i1 + 1, N - 1);
        float y1 = b.sample(i1, ch);
        float y2 = b.sample(i2, ch);
        return static_cast<float>((1.0 - frac) * y1 + frac * y2);
    }

    // Cubic: gather neighbors with edge clamping
    size_t i0 = (i1 == 0) ? 0 : i1 - 1;
    size_t i2 = std::min(i1 + 1, N - 1);
    size_t i3 = std::min(i1 + 2, N - 1);

    float y0 = b.sample(i0, ch);
    float y1 = b.sample(i1, ch);
    float y2 = b.sample(i2, ch);
    float y3 = b.sample(i3, ch);

    return interp_cubic(y0, y1, y2, y3, static_cast<float>(frac));
}
