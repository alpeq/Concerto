import sys

dynapse1_path = "./dynap-se1"
if dynapse1_path not in sys.path:
    sys.path.append(dynapse1_path)

import samna
import numpy as np
import matplotlib

#matplotlib.use("TkAgg")          # Or "Qt5Agg", "MacOSX", "WebAgg"
import samna.dynapse1 as dyn1

import dynapse1utils as ut
from netgen import Neuron, NetworkGenerator
from params import *
import time
import importlib
from collections import deque
import threading

eventsBuffer = deque(maxlen=500)

def collect_spikes(sink_node):
    while True:  # Check first element of list
        eventsBuffer.extend(sink_node.get_events())

def main():
    # Setup Dynapse1
    devices = samna.device.get_unopened_devices()
    print(devices)

    #model = samna.device.open_device(devices[int(0)])
    #api = model.get_dynapse1_api()
    model, _ = ut.open_dynapse1(gui=False, select_device=True)
    api = model.get_dynapse1_api()

    # To the Oscilloscope
    #chip_id = 1
    #neuron_id = 10 # neuron id is different than in the monitored neurons since they dont define Core_ID
    #api.monitor_neuron(chip_id, neuron_id)

    # apply the configuration
    # initiate network
    net_gen = NetworkGenerator()
    net_gen.clear_network()
    new_config = net_gen.make_dynapse1_configuration()
    model.apply_configuration(new_config)

    # Set hardware parameters
    set_params(model)

    monitored_neurons = [(0,1,10),(2,3,77)] # Chip_ID ({0-3}, Core_ID {0-3}, Neuron_ID {0-257} )
                                            #(n.chip_id, n.core_id, n.neuron_id)
    graph, filter_node, sink_node = ut.create_neuron_select_graph(model, monitored_neurons)
    graph.start() # It needs to be started

    # clear the buffer
    sink_node.get_events()

    # select the neurons to monitor
    filter_node.set_neurons(monitored_neurons)

    api.reset_timestamp()

    spike_thread = threading.Thread(target=collect_spikes, args=sink_node)
    spike_thread.daemon = True
    spike_thread.start()

    from live_gui.sliderGui import run_threaded_gui
    run_threaded_gui(model)

    print(eventsBuffer)


if __name__ == "__main__":
    main()
