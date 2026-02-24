#include <portaudio.h>

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


struct Engine {
    AudioBuffer buffer;
    SamplerVoice voice{&buffer};

    int outChannels = 2;
    unsigned long framesPerBuffer = 256;

    std::atomic<bool> running{true};
};

static int pa_callback(const void*, void* outputBuffer,
                       unsigned long framesPerBuffer,
                       const PaStreamCallbackTimeInfo*,
                       PaStreamCallbackFlags,
                       void* userData)
{
    auto* e = static_cast<Engine*>(userData);
    float* out = static_cast<float*>(outputBuffer);

    // Clear first (safe)
    std::fill(out, out + framesPerBuffer * e->outChannels, 0.0f);

    e->voice.render(out, framesPerBuffer, e->outChannels);
    return e->running.load() ? paContinue : paComplete;
}

