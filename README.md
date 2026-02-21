# Amplify
Senior Project for Jake Model, Jaydon Faal, Alex Lott, and Sophia Kager

Amplify is a CLI tool for audio manipulation (load, scale, loop, mix, export).

## Development Install

pip install -e .

## Example Usage

amplify init song.yml
amplify load song.yml kick.wav snare.wav
amplify scale song.yml kick --factor 1.2 --preserve-pitch
amplify loop song.yml snare --count 4
amplify mix song.yml --no-normalize
amplify export song.yml out.wav
