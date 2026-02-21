# Amplify
Senior Project for Jake Model, Jaydon Faal, Alex Lott, and Sophia Kager

Amplify is a CLI tool for audio manipulation (load, scale, loop, mix, export).

## Development Install

pip install -e .

## Example Usage

amplify init song.yml \n
amplify load song.yml kick.wav snare.wav \n
amplify scale song.yml kick --factor 1.2 --preserve-pitch \n
amplify loop song.yml snare --count 4 \n
amplify mix song.yml --no-normalize \n
amplify export song.yml out.wav \n
