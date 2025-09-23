# -*- coding: utf-8 -*-
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
import yaml
import time
import rtmidi
import queue
import heapq

from Concerto.example_texel import setup_parameters
from texel_api import *

class Config():
    def __init__(self,filename, attribute):
        with open(filename, 'r') as f:
            params = yaml.safe_load(f)
        self.params_dict = params[attribute]
        self.fill_parameters()

    def fill_parameters(self):
        for key, value in self.params_dict.items():
            setattr(self, key, value)


class Subject(ABC):
    """
    The Subject interface declares a set of methods for managing subscribers.
    """
    def __init__(self):
        self._observers: List[Observer] = []
    def attach(self, observer: Observer) -> None:
        print("Subject: Attached an observer.")
        self._observers.append(observer)
    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)
    """
    The subscription management methods.
    """
    def notify(self) -> None:
        """
        Trigger an update in each subscriber.
        """
        for observer in self._observers:
            observer.update(self)

class Observer(ABC):
    """
    The Observer interface declares the update method, used by subjects.
    """
    @abstractmethod
    def update(self, subject: Subject) -> None:
        """
        Receive update from subject.
        """
        pass

class NeuroListener(Subject):
    ''' Dummy class with list of events times and ids '''
    def __init__(self, times, ids):
        super().__init__()
        self.times = times
        self.ids = ids
        self._event = None
    def setup(self):
        ''' Setup the port to connect '''
        pass
    def cleanup(self):
        pass
    ''' '''
    def start_event_listener(self):
        ''' Class to fill per Hardware platform inherited'''
        pass
    def start_streaming_events(self):
        tm1 = self.times[0]
        for t,id in zip(self.times, self.ids):
            #time.sleep() preproccess the alld diff= t -(t-1) before hand does sleep work at ms?
            self._event = id
            #self._duration = (t-tm1)/1000000
            self.notify()
            tm1 = t
            #time.sleep(0.001)


class NeuroListener_Texel(NeuroListener):
    """
    SensorStatus is a Subject node that notifies the status of each of the sensors for motor control and logging
    """
    def __init__(self, parameters, flags):
        self.chip = texel_interface(parameters=parameters, flags=flags, serial_port='/dev/ttyACM0')
        self.clean()

    def clean(self):
        # Reset Chip
        self.chip.setup()
        time.sleep(0.1)
        self.chip.reset()
        self.chip.write_all_registers()
        self.chip.reset(which='synapses')
        time.sleep(1)

    def clean_sensor_reading(self):
        self._reading_flag = False
    def activate_sensor_reading(self):
        self._reading_flag = True

    def start_sensor_reading(self, debug=False) -> None:
        """
        Loop to read sensors
        """
        pass


class OrchestraGenerator(Observer):
    def __init__(self, params, debug=False, default_duration=0.1, default_velocity=100, max_queue=500):
        self.debug = debug
        self.notes_id = params.id
        self.params_dict = params.params_dict
        self.default_duration = default_duration
        self.default_velocity = default_velocity
        self.max_queue = max_queue

        self.midiout = rtmidi.MidiOut()
        self.setup_midi_comm(0)

        # Deduplication: only latest per note_id
        self.event_queue = queue.Queue()
        self.pending_notes = {}   # note_id -> (note_id, duration, velocity)
        self.note_off_heap = []   # (timestamp, note_id)
        self.running = True

        # Worker thread
        self.worker = threading.Thread(target=self._player_loop, daemon=True)
        self.worker.start()

    def setup_midi_comm(self, port_id):
        available_ports = self.midiout.get_ports()
        if available_ports:
            self.midiout.open_port(port_id)
        else:
            self.midiout.open_virtual_port("My virtual output")

    def cleanup(self):
        self.running = False
        self.worker.join()
        if self.midiout.is_port_open():
            self.midiout.close_port()
        del self.midiout

    def silence(self):
        """All notes off (MIDI CC 123)."""
        self.midiout.send_message([0xB0, 123, 0])

    def update(self, subject: "Subject"):
        """Observer callback: enqueue latest event (note, duration, velocity)."""
        note_id = self.notes_id[subject._event]
        #duration = getattr(subject, "duration", self.default_duration)
        duration = self.default_duration
        velocity = getattr(subject, "velocity", self.default_velocity)

        # Replace any pending event for this note_id
        self.pending_notes[note_id] = (note_id, duration, velocity)

        # Drop if too many different notes pending
        if len(self.pending_notes) > self.max_queue:
            oldest_note = next(iter(self.pending_notes))
            del self.pending_notes[oldest_note]

        # Push note_id marker to queue
        self.event_queue.put(note_id)

        if self.debug:
            print(f"Queued/replaced note {note_id}, vel={velocity}, dur={duration:.2f}s")

    def _player_loop(self):
        while self.running:
            now = time.time()

            # Process new events
            try:
                while True:
                    note_id = self.event_queue.get_nowait()

                    if note_id not in self.pending_notes:
                        continue

                    note_id, duration, velocity = self.pending_notes.pop(note_id)

                    self.midiout.send_message([0x90, note_id, velocity])
                    heapq.heappush(self.note_off_heap, (now + duration, note_id))
                    if self.debug:
                        print(f"Note on {note_id}, vel={velocity}, off at {now + duration:.3f}")
            except queue.Empty:
                pass

            # Process note_off events that are due
            while self.note_off_heap and self.note_off_heap[0][0] <= now:
                _, note_id = heapq.heappop(self.note_off_heap)
                self.midiout.send_message([0x80, note_id, 0])
                if self.debug:
                    print(f"Note off {note_id} at {now:.3f}")

            time.sleep(0.001)  # avoid 100% CPU spin

