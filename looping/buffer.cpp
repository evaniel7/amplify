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



struct AudioBuffer {
    int sampleRate = 0;
    int channels = 0; // channel 1 for mono and channel 2 for stereo
    std::vector<float> data; // Stereo: [L,R,L,R,...], Mono [M,M,...]

    size_t frame_count() const {
        if (channels <= 0) return 0;
        return data.size() / static_cast<size_t>(channels); // gives the number of frames
    }

    float sample(size_t frameIndex, int ch) const {
        frameIndex = std::min(frameIndex, frame_count() ? frame_count() - 1 : 0); // ensures frame index isn't out of range
        ch = std::clamp(ch, 0, channels - 1); //ensures ch is in range so we can go thru our frame-channel matrix 
        return data[frameIndex * static_cast<size_t>(channels) + static_cast<size_t>(ch)]; //turns 2d frame-channel table into 1d, so index = frameINdex*channels +ch
                                                                                        // frame 0 = index 0,1, frame 1 = 2,3...
    }
};