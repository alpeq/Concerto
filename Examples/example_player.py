"""
Project: Concerto
Description: Example to test midi generation

Code owner: Alejandro Pequeno-Zurro, https://github.com/alpeq/Concerto

Contributors: Adrian Whatley, Mirco Tincani

License MIT
"""

import asyncio
import time
from collections import deque
import numpy as np
import pyaudio

# Audio constants
RATE = 44100  # Sample rate
CHUNK = 1024  # Samples per buffer
FREQ_BASE = 220.0  # Base frequency (Hz)

# Audio stream generator
def generate_tone(freq):
    """Generate sine wave tone for given frequency."""
    t = (np.arange(CHUNK) / RATE).astype(np.float32)
    wave = 0.5 * np.sin(2 * np.pi * freq * t)
    return wave.astype(np.float32).tobytes()

# Audio player class
class AudioServer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=RATE,
                                  output=True)

    def play(self, freq):
        tone = generate_tone(freq)
        self.stream.write(tone)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

# Main function
async def monitor_event_rate(event_stream, duration=30):
    """Monitors incoming events and adjusts tone frequency."""
    audio = AudioServer()
    event_times = deque()
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            # Wait for event or timeout
            try:
                event = await asyncio.wait_for(event_stream.get(), timeout=0.1)
                now = time.time()
                event_times.append(now)

                # Keep only events from the last second
                while event_times and now - event_times[0] > 1.0:
                    event_times.popleft()

                rate = len(event_times)  # events per second
                freq = FREQ_BASE + rate * 10  # simple modulation rule

                print(f"[{round(now,2)}] Event rate: {rate} Hz | Playing freq: {round(freq,1)} Hz")
                audio.play(freq)

            except asyncio.TimeoutError:
                # No event, play base tone
                audio.play(FREQ_BASE)
    finally:
        audio.close()

# Simulated event stream
async def simulate_events(event_stream):
    """Simulates random events pushed into a queue."""
    while True:
        await asyncio.sleep(np.random.exponential(0.2))  # Random interval
        await event_stream.put({'event': 'something'})

# Entry point
async def main():
    event_stream = asyncio.Queue()
    producer = asyncio.create_task(simulate_events(event_stream))
    consumer = asyncio.create_task(monitor_event_rate(event_stream))
    await asyncio.gather(producer, consumer)

if __name__ == "__main__":
    asyncio.run(main())
