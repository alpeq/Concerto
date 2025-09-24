# -*- coding: utf-8 -*-
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
import yaml
import time
import rtmidi
import queue
import heapq
import random

from Concerto.example_texel import setup_parameters
#from Samna_demo import chip_id
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
            time.sleep(0.005)


class NeuroListener_Texel(Subject):
    """
    SensorStatus is a Subject node that notifies the status of each of the sensors for motor control and logging
    """
    def __init__(self, parameters, flags, core, neuron_list):
        super().__init__()
        self.chip = texel_interface(parameters=parameters, flags=flags, serial_port='/dev/ttyACM0')
        self.core = core
        self.n_list = neuron_list
        self.clean()
        self.setup_sample_parameters()
        self.stimulator = threading.Thread(target=self._send_spikes, daemon=True)
        self._streaming_flag = True

    def _send_spikes(self):
        for neuron_id in self.neulist:
            for i in range(100):
#                if random.random() < 0.5:
                self.chip.send_spike(core=self.core, neuron_idx=neuron_id, synapse_idx=(0))
                self.chip.send_spike(core=self.core, neuron_idx=neuron_id, synapse_idx=(0))

    def start_stimulation(self):
        self.stimulator.start()

    def clean(self):
        # Reset Chip
        self.chip.setup()
        time.sleep(0.1)
        self.chip.reset()
        self.chip.write_all_registers()
        self.chip.reset(which='synapses')
        time.sleep(1)

    def setup_sample_parameters(self):
        for n in self.n_list:
            self.chip.activate_neuron_monitor(core=0, neuron_idx=n)
            self.chip.activate_synapse_monitor(core=0, neuron_idx=n, synapse_idx=0)
        self.sample_parameter_network()

    def start_event_listener(self, debug=False) -> None:
        """
        Loop to read events
        """
        tm1 = 0
        self.chip.start_experiment()
        while self._streaming_flag:
            time.sleep(0.001)
            s_ts, s_id = self.chip.report_neural_activity()
            if not s_ts:
                continue
            for ts,id in zip(s_ts, s_id):
                self._event = id
                # self._duration = ((ts-tm1)/1000000 if tm1!=0 else 0)
                self.notify()
                tm1 = ts
            #time.sleep(0.005)


    def sample_parameter_network(self):
        self.chip.update_parameter(core=0, param="neuron_ref_NFI", value=100e-12)
        self.chip.update_parameter(core=0, param="neuron_gain_NFI", value=2e-12)
        self.chip.update_parameter(core=0, param="neuron_starve_NFI", value=1e-9)
        self.chip.update_parameter(core=0, param="neuron_spkthr_PFI", value=10e-9)
        self.chip.update_parameter(core=0, param="neuron_tau_NFI", value=10e-12)
        self.chip.update_parameter(core=0, param='ssynapse_w_NFI', value=100e-9)  # exc
        self.chip.update_parameter(core=0, param='ssynapse_w_PFI', value=1e-9)  # inh
        self.chip.update_parameter(core=0, param='static_exc_gain_PFI', value=1e-12)
        self.chip.update_parameter(core=0, param='static_exc_tau_PFI', value=1e-12)
        self.chip.update_parameter(core=0, param='static_inh_gain_NFI', value=1e-12)
        self.chip.update_parameter(core=0, param='static_inh_tau_NFI', value=1e-12)
        self.chip.update_parameter(core=0, param='plastic_right_tau_PFI', value=1e-12)
        self.chip.update_parameter(core=0, param='plastic_right_gain_PFI', value=1e-12)
        self.chip.update_parameter(core=0, param='bypass_tail_w1_NFI', value=100e-9)
        self.chip.update_parameter(core=0, param='ahp_pw_PFI', value=1e-9)  # used to control post-pulse width
        self.chip.update_parameter(core=0, param='pw_read_pot_PFI', value=1e-9)  # used to control pre-pulse width

        self.chip.set_synapse_weight(core=0, neuron_idx=0, synapse_idx=(0), value=1)

    def stop_listener(self):
        self._streaming_flag = False
        self.chip.uC.stop_experiment()

''' OBSERVERS - Midi Generator '''
class OrchestraGenerator(Observer):
    def __init__(self, params, debug=False, default_duration=0.001, default_velocity=100, max_queue=500):
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
        #print(subject._event)
        note_id = (self.notes_id.get(subject._event) if not None else int(subject._event))
        #duration = getattr(subject, "duration", self.default_duration)
        duration = self.default_duration
        velocity = getattr(subject, "velocity", self.default_velocity)

        # Replace any pending event for this note_id
        self.pending_notes[note_id] = (note_id, duration, velocity)

        # Drop if too many different notes pending in the queue
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
                    # It may have deleted in the process
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

