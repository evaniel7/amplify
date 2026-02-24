#include <portaudio.h>
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


struct Options {
    fs::path file;
    std::optional<double> loopStartSec;
    std::optional<double> loopEndSec;
    double rate = 1.0;
    int xfadeMs = 0;
    Interp interp = Interp::Cubic;
};

static void usage(const char* argv0) {
    std::cerr
        << "Usage: " << argv0 << " <file.wav> [options]\n"
        << "Options:\n"
        << "  --loop-start <sec>   loop start time in seconds\n"
        << "  --loop-end <sec>     loop end time in seconds\n"
        << "  --xfade-ms <ms>      crossfade length in milliseconds (0 disables)\n"
        << "  --rate <r>           playback rate (1.0 normal, >1 pitch up, <1 pitch down)\n"
        << "  --interp linear|cubic\n";
}

static Options parse_args(int argc, char** argv) {
    if (argc < 2) {
        usage(argv[0]);
        throw std::runtime_error("Missing input file.");
    }

    Options opt;
    opt.file = argv[1];

    for (int i = 2; i < argc; i++) {
        std::string a = argv[i];

        auto need = [&](const char* name) -> std::string {
            if (i + 1 >= argc) throw std::runtime_error(std::string("Missing value for ") + name);
            return argv[++i];
        };

        if (a == "--loop-start") {
            opt.loopStartSec = std::stod(need("--loop-start"));
        } else if (a == "--loop-end") {
            opt.loopEndSec = std::stod(need("--loop-end"));
        } else if (a == "--xfade-ms") {
            opt.xfadeMs = std::stoi(need("--xfade-ms"));
        } else if (a == "--rate") {
            opt.rate = std::stod(need("--rate"));
        } else if (a == "--interp") {
            std::string v = need("--interp");
            if (v == "linear") opt.interp = Interp::Linear;
            else if (v == "cubic") opt.interp = Interp::Cubic;
            else throw std::runtime_error("interp must be linear|cubic");
        } else {
            throw std::runtime_error("Unknown arg: " + a);
        }
    }

    return opt;
}