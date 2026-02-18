###########################################################################
#
# # Numerical Astrodynamics 2025/2026
#
# # Assignment 1 - Propagation Settings
#
###########################################################################


""" 
Copyright (c) 2010-2020, Delft University of Technology
All rights reserved

This file is part of Tudat. Redistribution and use in source and 
binary forms, with or without modification, are permitted exclusively
under the terms of the Modified BSD license. You should have received
a copy of the license with this file. If not, please or visit:
http://tudat.tudelft.nl/LICENSE.
"""

import os

import numpy as np
from matplotlib import pyplot as plt
from tudatpy import constants
from tudatpy.data import save2txt
from tudatpy.interface import spice
from tudatpy.dynamics import environment_setup, propagation_setup, simulator

# Retrieve current directory
current_directory = os.getcwd()

# # student number: 1244779 --> 1244ABC
A = 3
B = 5
C = 6

simulation_start_epoch = (
    35.4 * constants.JULIAN_YEAR
    + A * 7.0 * constants.JULIAN_DAY
    + B * constants.JULIAN_DAY
    + C * constants.JULIAN_DAY / 24.0
)
simulation_end_epoch = simulation_start_epoch + 344.0 * constants.JULIAN_DAY / 24.0

###########################################################################
# CREATE ENVIRONMENT ######################################################
###########################################################################

# Load spice kernels.
spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

# Create settings for celestial bodies
bodies_to_create = ["Ganymede"]
global_frame_origin = "Ganymede"
global_frame_orientation = "ECLIPJ2000"
body_settings = environment_setup.get_default_body_settings(
    bodies_to_create, global_frame_origin, global_frame_orientation
)


###########################################################################
# CREATE VEHICLE ##########################################################
###########################################################################

body_settings.add_empty_settings("JUICE")

# Create environment
bodies = environment_setup.create_system_of_bodies(body_settings)

###########################################################################
# CREATE ACCELERATIONS ####################################################
###########################################################################

# Define bodies that are propagated, and their central bodies of propagation.
bodies_to_propagate = ["JUICE"]
central_bodies = ["Ganymede"]

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle = dict(Ganymede=[propagation_setup.acceleration.point_mass_gravity()])

# Create global accelerations dictionary.
acceleration_settings = {"JUICE": acceleration_settings_on_vehicle}

# Create acceleration models.
acceleration_models = propagation_setup.create_acceleration_models(
    bodies, acceleration_settings, bodies_to_propagate, central_bodies
)

###########################################################################
# CREATE PROPAGATION SETTINGS #############################################
###########################################################################

# Define initial state.
system_initial_state = spice.get_body_cartesian_state_at_epoch(
    target_body_name="JUICE",
    observer_body_name="Ganymede",
    reference_frame_name="ECLIPJ2000",
    aberration_corrections="NONE",
    ephemeris_time=simulation_start_epoch,
)

# Define required outputs
dependent_variables_to_save = [
    propagation_setup.dependent_variable.keplerian_state( "JUICE", "Ganymede" )
]

# Create numerical integrator settings.
fixed_step_size = 10.0
integrator_settings = propagation_setup.integrator.runge_kutta_fixed_step(
    fixed_step_size, coefficient_set=propagation_setup.integrator.CoefficientSets.rk_4
)

# Create propagation settings.
termination_settings = propagation_setup.propagator.time_termination(
    simulation_end_epoch
)
propagator_settings = propagation_setup.propagator.translational(
    central_bodies,
    acceleration_models,
    bodies_to_propagate,
    system_initial_state,
    simulation_start_epoch,
    integrator_settings,
    termination_settings,
    output_variables=dependent_variables_to_save,
)

propagator_settings.print_settings.print_initial_and_final_conditions = True


###########################################################################
# PROPAGATE ORBIT #########################################################
###########################################################################

# Create simulation object and propagate dynamics.
dynamics_simulator = simulator.create_dynamics_simulator(
    bodies, propagator_settings
)

# Retrieve all data produced by simulation
propagation_results = dynamics_simulator.propagation_results

# Extract numerical solution for states and dependent variables
state_history = propagation_results.state_history
dependent_variables = propagation_results.dependent_variable_history

###########################################################################
# SAVE RESULTS ############################################################
###########################################################################

save2txt(
    solution=state_history, filename="JUICEPropagationHistory_Q1.dat", directory="./"
)

save2txt(
    solution=dependent_variables,
    filename="JUICEPropagationHistory_DependentVariables_Q1.dat",
    directory="./",
)

###########################################################################
# PLOT RESULTS ############################################################
###########################################################################

# Extract time and Kepler elements from dependent variables
kepler_elements = np.vstack(list(dependent_variables.values()))
# print(kepler_elements.shape)
time = dependent_variables.keys()
time_days = [
    t / constants.JULIAN_DAY - simulation_start_epoch / constants.JULIAN_DAY
    for t in time
]

# Ensure the 'figures' directory exists
output_dir = os.path.join(current_directory, "figures")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Extract time and Kepler elements from dependent variables
# Note: Ensure the dictionary is sorted by time before stacking
sorted_indices = np.argsort(list(dependent_variables.keys()))
# kepler_elements = np.vstack(list(dependent_variables.values()))[sorted_indices]

# time = np.array(list(dependent_variables.keys()))[sorted_indices]
# time_days = (time - simulation_start_epoch) / constants.JULIAN_DAY

# 1. Get the initial Kepler elements (at t0)
initial_state = kepler_elements[0, :]

# 2. Calculate the change w.r.t t0 (Element(t) - Element(t0))
delta_kepler = kepler_elements - initial_state

# 3. Prepare labels and unit conversions for the 6 Kepler elements
# Tudat Order: a, e, i, omega, Omega, theta
titles = [
    "Semi-major Axis (a)",
    "Eccentricity (e)",
    "Inclination (i)",
    "Argument of Periapsis (\u03C9)",
    "Longitude of Ascending Node (\u03A9)",
    "True Anomaly (\u03B8)"
]

y_labels = [
    "$\Delta a$ [m]",
    "$\Delta e$ [-]",
    "$\Delta i$ [deg]",
    "$\Delta \omega$ [deg]",
    "$\Delta \Omega$ [deg]",
    "$\Delta \\theta$ [deg]"
]

# Convert angular differences (indices 2 to 5) from Radians to Degrees for readability
delta_kepler[:, 2:6] = np.rad2deg(delta_kepler[:, 2:6])

# 4. Generate the plot
fig, axs = plt.subplots(3, 2, figsize=(15, 12))
# fig.suptitle(f'Change in JUICE Kepler Elements w.r.t $t_0$ (Frame: {global_frame_orientation})', fontsize=16)

# Flatten the axes array for easy iteration (0 to 5)
axs_flat = axs.flatten()

for i in range(6):
    axs_flat[i].plot(time_days, delta_kepler[:, i])
    axs_flat[i].set_title(titles[i])
    axs_flat[i].set_xlabel('Time since $t_0$ [days]')
    axs_flat[i].set_ylabel(y_labels[i])
    axs_flat[i].grid(True)
    axs_flat[i].ticklabel_format(useOffset=False) # Prevents confusing scientific notation offsets

# Improve layout spacing
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# 5. Save the figure
output_path = os.path.join(output_dir, "change_in_kepler_elements_q1.pdf")
plt.savefig(output_path)
print(f"Plot saved to: {output_path}")

# Optional: Show plot if running interactively
# plt.show()
plt.close()
