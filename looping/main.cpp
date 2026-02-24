#include <portaudio.h>
#include "cli_parsing.cpp"
#include "interpolation.cpp"
#include "port_audio.cpp"
#include "sample_voice.cpp"
#include "utility.cpp"
#include "loader.cpp"
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


int main(int argc, char** argv) {
    try {
        Options opt = parse_args(argc, argv);

        Engine engine;
        engine.buffer = load_wav_to_float(opt.file);

        // Loop region in frames
        const size_t totalFrames = engine.buffer.frames();
        auto sec_to_frame = [&](double sec) -> size_t {
            if (sec < 0) sec = 0;
            double f = sec * static_cast<double>(engine.buffer.sampleRate);
            return static_cast<size_t>(std::llround(f));
        };

        LoopRegion r{0, totalFrames};
        if (opt.loopStartSec) r.startFrame = std::min(sec_to_frame(*opt.loopStartSec), totalFrames);
        if (opt.loopEndSec)   r.endFrame   = std::min(sec_to_frame(*opt.loopEndSec), totalFrames);

        if (r.endFrame <= r.startFrame) {
            // fallback
            r.startFrame = 0;
            r.endFrame = totalFrames;
        }

        engine.voice.set_loop(true);
        engine.voice.set_loop_region(r);
        engine.voice.set_rate(opt.rate);
        engine.voice.set_interp(opt.interp);

        size_t xfadeFrames = 0;
        if (opt.xfadeMs > 0) {
            xfadeFrames = static_cast<size_t>(
                (static_cast<double>(opt.xfadeMs) / 1000.0) * engine.buffer.sampleRate
            );
        }
        engine.voice.set_crossfade_frames(xfadeFrames);

        std::cout << "Loaded: " << opt.file << "\n";
        std::cout << "SR: " << engine.buffer.sampleRate << " Hz, Ch: " << engine.buffer.channels
                  << ", Frames: " << engine.buffer.frames() << "\n";
        std::cout << "Loop: [" << r.startFrame << ", " << r.endFrame << ") frames"
                  << "  xfadeFrames=" << xfadeFrames
                  << "  rate=" << opt.rate
                  << "  interp=" << (opt.interp == Interp::Linear ? "linear" : "cubic")
                  << "\n";
        std::cout << "Playing... press ENTER to stop.\n";

        // PortAudio setup
        PaError err = Pa_Initialize();
        if (err != paNoError) throw std::runtime_error("Pa_Initialize failed.");

        PaStream* stream = nullptr;
        err = Pa_OpenDefaultStream(
            &stream,
            0,                    // no input
            engine.outChannels,    // output channels (stereo)
            paFloat32,             // float output
            engine.buffer.sampleRate,
            engine.framesPerBuffer,
            pa_callback,
            &engine
        );
        if (err != paNoError) throw std::runtime_error("Pa_OpenDefaultStream failed.");

        err = Pa_StartStream(stream);
        if (err != paNoError) throw std::runtime_error("Pa_StartStream failed.");

        std::cin.get();

        engine.running.store(false);
        Pa_StopStream(stream);
        Pa_CloseStream(stream);
        Pa_Terminate();

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}