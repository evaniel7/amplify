#ifndef BUFFER_CPP_INCLUDED
#define BUFFER_CPP_INCLUDED

#include <algorithm>
#include <vector>

struct AudioBuffer {
    int sampleRate = 0;
    int channels = 0;                // 1=mono, 2=stereo
    std::vector<float> data;         // Stereo: [L,R,L,R,...], Mono: [M,M,...]

    size_t frame_count() const {
        if (channels <= 0) return 0;
        return data.size() / static_cast<size_t>(channels);
    }

    // Alias used by the rest of your codebase
    size_t frames() const { return frame_count(); }

    float sample(size_t frameIndex, int ch) const {
        const size_t fc = frame_count();
        frameIndex = std::min(frameIndex, fc ? fc - 1 : 0);
        ch = std::clamp(ch, 0, channels - 1);
        return data[frameIndex * static_cast<size_t>(channels) + static_cast<size_t>(ch)];
    }
};

#endif // BUFFER_CPP_INCLUDED