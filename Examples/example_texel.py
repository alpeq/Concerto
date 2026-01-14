"""
Project: Concerto
Description: Example to connect to Texel chip and collect events

Code owner: Alejandro Pequeno-Zurro, https://github.com/alpeq/Concerto

Contributors: Adrian Whatley, Mirco Tincani

License MIT
"""
import sys
#sys.path.append("..")
import matplotlib.pyplot as plt
import numpy as np
import time
from texel_api import *
from texel_params import *

''' If it does not work reset with white button, or flash it with arduine IDE'''

def setup_parameters(chip, neuron_id):
    chip.update_parameter(core=0, param="neuron_ref_NFI", value=100e-12)
    chip.update_parameter(core=0, param="neuron_gain_NFI", value=2e-12)
    chip.update_parameter(core=0, param="neuron_starve_NFI", value=1e-9)
    chip.update_parameter(core=0, param="neuron_spkthr_PFI", value=10e-9)
    chip.update_parameter(core=0, param="neuron_tau_NFI", value=10e-12)

    chip.update_parameter(core=0, param='ssynapse_w_NFI', value=100e-9) #exc
    chip.update_parameter(core=0, param='ssynapse_w_PFI', value=1e-9) #inh
    chip.update_parameter(core=0, param='static_exc_gain_PFI', value=1e-12)
    chip.update_parameter(core=0, param='static_exc_tau_PFI', value=1e-12)
    chip.update_parameter(core=0, param='static_inh_gain_NFI', value=1e-12)
    chip.update_parameter(core=0, param='static_inh_tau_NFI', value=1e-12)

    chip.update_parameter(core=0, param='plastic_right_tau_PFI', value=1e-12)
    chip.update_parameter(core=0, param='plastic_right_gain_PFI', value=1e-12)
    chip.update_parameter(core=0, param='bypass_tail_w1_NFI', value=100e-9)

    chip.update_parameter(core=0, param='ahp_pw_PFI', value=1e-9) #used to control post-pulse width
    chip.update_parameter(core=0, param='pw_read_pot_PFI', value=1e-9) #used to control pre-pulse width

    chip.set_synapse_weight(core=0, neuron_idx=0, synapse_idx=(0), value=1)



def poisson_spike_train(frequency, duration=1, time_resolution=1e-6):

    time_points = np.arange(0, duration, time_resolution)
    num_time_points = len(time_points)

    # Calculate the probability of a spike at each time point
    spike_prob = frequency * time_resolution

    # Generate a random spike train based on the Poisson process
    spike_train = np.random.rand(num_time_points) < spike_prob

    return spike_train, time_points


def main():

    chip = texel_interface(parameters=parameters, flags=flags, serial_port='/dev/ttyACM0')

    # Reset Chip
    chip.setup()
    time.sleep(0.1)
    chip.reset()
    chip.write_all_registers()
    chip.reset(which='synapses')
    time.sleep(1)

    # Setup neurons and monitor
    neulist = [1,10,20]

    for neuron_id in neulist:
        chip.activate_neuron_monitor(core=0, neuron_idx=neuron_id)
        chip.activate_synapse_monitor(core=0, neuron_idx=neuron_id, synapse_idx=0)
        setup_parameters(chip, neuron_id)

    chip.start_experiment()

    for neuron_id in neulist:
        for i in range(10):
            chip.send_spike(core=0, neuron_idx=neuron_id, synapse_idx=(0))
            chip.send_spike(core=0, neuron_idx=neuron_id, synapse_idx=(0))

    time.sleep(1)
    chip.uC.stop_experiment()
    spike_times, spikes = chip.report_neural_activity()

    print(spike_times)
    print(spikes)

if __name__ == "__main__":
    main()
