#include <portaudio.h>
#include "buffer.cpp"
#include "interpolation.cpp"
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



struct LoopRegion {
    size_t startFrame = 0; // inclusive
    size_t endFrame = 0;   // exclusive (endFrame > startFrame)
};

class SamplerVoice {
public:
    explicit SamplerVoice(const AudioBuffer* buf)
        : buffer_(buf) {}

    void set_loop(bool enabled) { loopEnabled_.store(enabled); }
    void set_loop_region(LoopRegion r) { loop_.store(r); }
    void set_crossfade_frames(size_t frames) { xfadeFrames_.store(frames); }
    void set_rate(double rate) { rate_.store(rate); }
    void set_interp(Interp i) { interp_.store(i); }

    void reset(double framePos = 0.0) { pos_.store(framePos); }

    // Render interleaved float frames into out (stereo)
    void render(float* outInterleaved, unsigned long frames, int outChannels) {
        if (!buffer_ || buffer_->frames() == 0) {
            std::fill(outInterleaved, outInterleaved + frames * outChannels, 0.0f);
            return;
        }

        const AudioBuffer& b = *buffer_;
        const size_t totalFrames = b.frames();
        const int inCh = b.channels;
        const int chOut = outChannels;

        // Load atomics once per block to avoid tearing
        const bool loopEnabled = loopEnabled_.load();
        LoopRegion loop = loop_.load();
        size_t xfadeN = xfadeFrames_.load();
        double rate = rate_.load();
        Interp ip = interp_.load();

        // Fallback loop region: whole file
        if (!loopEnabled || loop.endFrame <= loop.startFrame || loop.endFrame > totalFrames) {
            loop.startFrame = 0;
            loop.endFrame = totalFrames;
        }

        // Crossfade cannot exceed loop length
        size_t loopLen = loop.endFrame - loop.startFrame;
        if (xfadeN > loopLen) xfadeN = loopLen;

        double pos = pos_.load();

        for (unsigned long f = 0; f < frames; f++) {
            float L = 0.0f, R = 0.0f;

            // Wrap logic: keep pos in [loop.start, loop.end)
            if (loopEnabled) {
                // If pos drifts outside, wrap it (also handles rate < 0 case roughly)
                while (pos < static_cast<double>(loop.startFrame)) pos += static_cast<double>(loopLen);
                while (pos >= static_cast<double>(loop.endFrame)) pos -= static_cast<double>(loopLen);
            } else {
                // If not looping and we hit end, output silence
                if (pos >= static_cast<double>(totalFrames)) {
                    L = R = 0.0f;
                    write_frame(outInterleaved, f, chOut, L, R);
                    continue;
                }
            }

            // Compute base sample
            auto getLR = [&](double p) {
                float l = 0.0f, r = 0.0f;
                if (inCh == 1) {
                    float m = sample_at(b, p, 0, ip);
                    l = m; r = m;
                } else {
                    l = sample_at(b, p, 0, ip);
                    r = sample_at(b, p, 1, ip);
                }
                return std::pair<float,float>(l,r);
            };

            // Crossfade near loop end: blend tail with loop start
            if (loopEnabled && xfadeN > 0) {
                double loopEnd = static_cast<double>(loop.endFrame);
                double fadeStart = loopEnd - static_cast<double>(xfadeN);
                if (pos >= fadeStart) {
                    double t01 = (pos - fadeStart) / static_cast<double>(xfadeN); // 0..1
                    t01 = clampf(static_cast<float>(t01), 0.0f, 1.0f);

                    // tail sample at pos
                    auto [l1, r1] = getLR(pos);

                    // corresponding head sample: map pos into start region
                    double headPos = static_cast<double>(loop.startFrame) + (pos - fadeStart);
                    // ensure headPos is in range
                    if (headPos >= static_cast<double>(loop.endFrame)) headPos -= static_cast<double>(loopLen);
                    auto [l2, r2] = getLR(headPos);

                    float g1 = xfade_a(static_cast<float>(t01));
                    float g2 = xfade_b(static_cast<float>(t01));
                    L = g1*l1 + g2*l2;
                    R = g1*r1 + g2*r2;
                } else {
                    auto [l, r] = getLR(pos);
                    L = l; R = r;
                }
            } else {
                auto [l, r] = getLR(pos);
                L = l; R = r;
            }

            write_frame(outInterleaved, f, chOut, L, R);

            // Advance
            pos += rate;
        }

        pos_.store(pos);
    }

private:
    static void write_frame(float* out, unsigned long frameIdx, int chOut, float L, float R) {
        if (chOut == 1) {
            out[frameIdx] = 0.5f*(L + R);
        } else {
            out[frameIdx*2 + 0] = L;
            out[frameIdx*2 + 1] = R;
        }
    }

    const AudioBuffer* buffer_ = nullptr;

    std::atomic<bool> loopEnabled_{true};
    std::atomic<LoopRegion> loop_{LoopRegion{0,0}};
    std::atomic<size_t> xfadeFrames_{0};
    std::atomic<double> rate_{1.0};
    std::atomic<Interp> interp_{Interp::Cubic};

    std::atomic<double> pos_{0.0};
};

