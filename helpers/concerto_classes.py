# -*- coding: utf-8 -*-
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
import yaml
import time
import rtmidi

from voluptuous import Object

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
        for t,id in zip(self.times, self.ids):
            #time.sleep() preproccess the alld diff= t -(t-1) before hand does sleep work at ms?
            self._event = id
            self.notify()


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


#message =
#    note_on = [0x90, 60, 120]
#    note_off = [0x80, 60, 10]
class OrchestraGenerator(Observer):
    def __init__(self, params, debug=False):
        self.debug = debug
        self.notes_id = params.id
        self.params_dict = params.params_dict
        self.midiout = rtmidi.MidiOut()
        self.setup_midi_comm(0)

    def setup_midi_comm(self, port_id):
        available_ports = self.midiout.get_ports()
        if self.debug:
            print(available_ports)
        if available_ports:
            self.midiout.open_port(port_id)
        else:
            self.midiout.open_virtual_port("My virtual output")

    def cleanup(self):
        if self.midiout.is_port_open():
            self.midiout.close_port()
        del self.midiout

    def build_message_sheet(self):
        pass
    def silence(self):
        self.midiout.send_message([0xB0,123,0]) # B0 or cc

    def update(self, subject: Subject):
        self.neuron_id = self.notes_id[subject._event]
        note_on = [0x90, self.neuron_id, 120]
        note_off = [0x80, self.neuron_id, 0]
        self.midiout.send_message(note_on)
        sleep(0.001)
        self.midiout.send_message(note_off)
        # Send on message
        if self.debug:
            print(self.neuron_id)
