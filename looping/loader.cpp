#include <portaudio.h>
#include <algorithm>
#include <atomic>
#include "buffer.cpp"
#include "utility.cpp"
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



static AudioBuffer load_wav_to_float(const fs::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("Failed to open: " + path.string());

    std::vector<uint8_t> file_in_bytes;
    in.seekg(0, std::ios::end); //measure file size
    auto sz = in.tellg(); //grabbing the end offset = file size in bytes as a stream position type
    if (sz < 0) throw std::runtime_error("Failed to size file."); //tekkg throws neg if there is an error
    in.seekg(0, std::ios::beg); //back to beginning
    file_in_bytes.resize(static_cast<size_t>(sz)); //change vector to hold sz bytes
    if (!file_in_bytes.empty()) in.read(reinterpret_cast<char*>(file_in_bytes.data()), sz);
    if (!in) throw std::runtime_error("Failed to read file: " + path.string()); //empty check before reading sz bytes in 

    if (file_in_bytes.size() < 12) throw std::runtime_error("File too small."); //wav header is 12 bytes
    if (std::memcmp(file_in_bytes.data(), "RIFF", 4) != 0 || std::memcmp(file_in_bytes.data() + 8, "WAVE", 4) != 0) {
        throw std::runtime_error("Not a RIFF/WAVE file.");
    }

    // Walk chunks
    size_t off = 12;
    bool foundFmt = false, foundData = false;
    uint16_t audioFormat = 0;
    uint16_t numChannels = 0;
    uint32_t sampleRate = 0;
    uint16_t bitsPerSample = 0;
    uint32_t dataSize = 0;
    size_t dataOff = 0;

    while (off + 8 <= b.size()) {
        const uint8_t* chunk = b.data() + off;
        char id[5] = {0,0,0,0,0};
        std::memcpy(id, chunk, 4);
        uint32_t chunkSize = read_u32_le(chunk + 4);
        off += 8;

        if (off + chunkSize > b.size()) throw std::runtime_error("Malformed WAV chunk size.");

        if (std::memcmp(id, "fmt ", 4) == 0) {
            if (chunkSize < 16) throw std::runtime_error("Malformed fmt chunk.");
            audioFormat   = read_u16_le(b.data() + off + 0);
            numChannels   = read_u16_le(b.data() + off + 2);
            sampleRate    = read_u32_le(b.data() + off + 4);
            bitsPerSample = read_u16_le(b.data() + off + 14);

            if (numChannels < 1 || numChannels > 2) {
                throw std::runtime_error("Only mono/stereo supported in this demo.");
            }
            foundFmt = true;
        } else if (std::memcmp(id, "data", 4) == 0) {
            dataSize = chunkSize;
            dataOff = off;
            foundData = true;
        }

        off += chunkSize;
        if (chunkSize % 2 == 1 && off < b.size()) off += 1; // word align
        if (foundFmt && foundData) break;
    }

    if (!foundFmt || !foundData) throw std::runtime_error("Missing fmt or data chunk.");

    // Convert to float buffer
    AudioBuffer out;
    out.sampleRate = static_cast<int>(sampleRate);
    out.channels = static_cast<int>(numChannels);

    const uint8_t* p = b.data() + dataOff;

    if (audioFormat == 1 && bitsPerSample == 16) {
        // PCM16
        if (dataSize % 2 != 0) throw std::runtime_error("PCM16 data size not aligned.");
        size_t samples = dataSize / 2;
        out.data.resize(samples);

        for (size_t i = 0; i < samples; i++) {
            int16_t s = static_cast<int16_t>(read_u16_le(p + 2*i));
            out.data[i] = static_cast<float>(s) / 32768.0f;
        }
    } else if (audioFormat == 3 && bitsPerSample == 32) {
        // IEEE float32
        if (dataSize % 4 != 0) throw std::runtime_error("Float32 data size not aligned.");
        size_t samples = dataSize / 4;
        out.data.resize(samples);
        for (size_t i = 0; i < samples; i++) {
            float f;
            std::memcpy(&f, p + 4*i, 4);
            out.data[i] = clampf(f, -1.0f, 1.0f);
        }
    } else {
        throw std::runtime_error("Unsupported WAV format. Use PCM16 or Float32.");
    }

    // Sanity: must have whole frames
    if (out.data.size() % static_cast<size_t>(out.channels) != 0) {
        throw std::runtime_error("Data not aligned to channel count.");
    }

    return out;
}

