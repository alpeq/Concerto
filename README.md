
# Concerto
**CONCERTO** is a hardware-agnostic, real-time spike-to-MIDI tool for neuromorphic systems. It enables interactive monitoring, tuning, and sonification of neural activity from neuromorphic hardware.

## Why CONCERTO?

* Enhance on-device tuning through real-time auditory feedback
* Monitor neural patterns and network dynamics
* Provide an intuitive demonstration tool for neuromorphic hardware

## What It Does

CONCERTO connects to neuromorphic devices (e.g., TEXEL, DYNAP-SE) and converts real-time spike streams into MIDI messages interpretable by electronic instruments.

## Key Features

* Real-time spike processing
* Hardware-agnostic event interface
* MIDI generation driven by neural dynamics
* Queue-based message handling with dropout

## Credits

This project was conceptualized, designed, and built during the BICS/NCS 2025 Workshop
by Alejandro Pequeno-Zurro, Adrian Whatley, and Mirco Tincani.
<img src="imgs/concerto_poster.jpg" alt="drawing" width="300"/>

# Requirements
* pip install python-rtmidi
* Recommended to test your midi communication on-device with an emulator such 
as vmpk (Virtual Midi Piano Keyboard) 
