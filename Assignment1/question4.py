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
from pathlib import Path

import numpy as np
from scipy.optimize import fsolve
from scipy.fftpack import fft, fftfreq
from matplotlib import pyplot as plt
from tudatpy import constants
from tudatpy.data import save2txt
from tudatpy.interface import spice
from tudatpy.dynamics import environment_setup, propagation_setup, simulator
from tudatpy.dynamics.propagation import create_dependent_variable_dictionary
from tudatpy.astro import element_conversion, frame_conversion
from tudatpy.util import result2array
from tudatpy import constants

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
simulation_end_epoch = simulation_start_epoch + 1e-3 * constants.JULIAN_DAY / 24.0 # debugging 
# simulation_end_epoch = simulation_start_epoch + 344.0 * constants.JULIAN_DAY / 24.0

# INPUT DATA FROM THE QUESTION IN THE ASSIGNMENT

# JUICE properties
drag_coeff_juice = 1.2
rad_pres_coeff_juice = 1.2
ref_area_juice = 100 # m^2
mass_juice = 2000 # kg

# environment properties
density_at_zero_altitude = 2e-9 # kg m^-3
density_scale_height = 40e3 # m 


###########################################################################
# CREATE ENVIRONMENT ######################################################
###########################################################################

# Load spice kernels.
spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

# Create settings for celestial bodies
bodies_to_create = ["Ganymede", "Jupiter", "Sun", "Saturn", "Europa", "Io", "Callisto"]
global_frame_origin = "Jupiter"
global_frame_orientation = "ECLIPJ2000"
body_settings = environment_setup.get_default_body_settings(
    bodies_to_create, global_frame_origin, global_frame_orientation
)

###########################################################################
# CREATE VEHICLE ##########################################################
###########################################################################

body_settings.add_empty_settings("JUICE")

# drag settings 
body_settings.get("Ganymede").atmosphere_settings = environment_setup.atmosphere.exponential(density_scale_height, density_at_zero_altitude)
aero_coefficient_settings = environment_setup.aerodynamic_coefficients.constant(
    ref_area_juice, [drag_coeff_juice, 0, 0])

# environment_setup.add_aerodynamic_coefficient_interface(bodies, "JUICE", aero_coefficient_settings)
body_settings.get("JUICE").aerodynamic_coefficient_settings = aero_coefficient_settings

# radiation pressure settings
occulting_bodies_dict = dict()
occulting_bodies_dict["Sun"] = ["Ganymede"]
# body_settings.get( "JUICE" ).radiation_pressure_target_settings = vehicle_target_settings
# vehicle_target_settings = environment_setup.radiation_pressure.cannonball_radiation_target(ref_area_juice,rad_pres_coeff_juice,occulting_bodies_dict)

occulting_bodies_dict = dict()
occulting_bodies_dict["Sun"] = ["Ganymede"]
vehicle_target_settings = environment_setup.radiation_pressure.cannonball_radiation_target(
    ref_area_juice, rad_pres_coeff_juice, occulting_bodies_dict )

# Add the radiation pressure interface to the body settings
body_settings.get("JUICE").radiation_pressure_target_settings = vehicle_target_settings

# Create environment
bodies = environment_setup.create_system_of_bodies(body_settings)
bodies.get_body("JUICE").mass = mass_juice

###########################################################################
# CREATE ACCELERATIONS ####################################################
###########################################################################

# Define bodies that are propagated, and their central bodies of propagation.
bodies_to_propagate = ["JUICE"]
central_bodies = ["Jupiter"] # this is the big change in this question

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle_perturbed = dict(
    Ganymede=[
        propagation_setup.acceleration.spherical_harmonic_gravity(2,2),
        propagation_setup.acceleration.aerodynamic()
    ],
    Jupiter=[
        propagation_setup.acceleration.spherical_harmonic_gravity(4,0)
    ],
    Sun=[propagation_setup.acceleration.point_mass_gravity(),
        propagation_setup.acceleration.radiation_pressure()  # CHECK
    ], 
    Saturn=[
        propagation_setup.acceleration.point_mass_gravity()
    ],
    Europa=[
        propagation_setup.acceleration.point_mass_gravity()
    ],
    Io=[
        propagation_setup.acceleration.point_mass_gravity()
    ],
    Callisto=[
        propagation_setup.acceleration.point_mass_gravity()
    ]
)

# Create global accelerations dictionary.
acceleration_settings_perturbed = {"JUICE": acceleration_settings_on_vehicle_perturbed}

# Create acceleration models.
acceleration_models_perturbed = propagation_setup.create_acceleration_models(
    bodies, 
    acceleration_settings_perturbed, 
    bodies_to_propagate, 
    central_bodies
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
# Get Ganymede gravitational parameter
ganymede_grav_param = bodies.get("Ganymede").gravitational_parameter
# print(ganymede_grav_param) # debugging
# Transform initial state to keplerian
system_initial_state_keplerian = element_conversion.cartesian_to_keplerian(system_initial_state, ganymede_grav_param)

# print(system_initial_state) # debugging

# Define required outputs
dependent_variables_to_save = [
    propagation_setup.dependent_variable.keplerian_state( "JUICE", "Ganymede" ),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.spherical_harmonic_gravity_type , "JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Io"),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Sun"),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.radiation_pressure_type , "JUICE", "Sun"),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.aerodynamic_type , "JUICE", "Ganymede" ),
    # propagation_setup.dependent_variable.dynamic_pressure("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.aerodynamic_force_coefficients("JUICE", "Ganymede"), # for doing sanity check on C_D
    # propagation_setup.dependent_variable.airspeed("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.density("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.radiation_pressure_coefficient("JUICE", "Sun"), # sanity check
    # propagation_setup.dependent_variable.body_mass("JUICE"), # sanity check
    # propagation_setup.dependent_variable.relative_position("JUICE", "Sun"),
    # propagation_setup.dependent_variable.tnw_to_inertial_rotation_matrix("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.body_fixed_airspeed_velocity("JUICE", "Ganymede")
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

propagator_settings_perturbed = propagation_setup.propagator.translational(
    central_bodies,
    acceleration_models_perturbed,
    bodies_to_propagate,
    system_initial_state,
    simulation_start_epoch,
    integrator_settings,
    termination_settings,
    output_variables=dependent_variables_to_save,
)

propagator_settings_perturbed.print_settings.print_initial_and_final_conditions = True


###########################################################################
# PROPAGATE ORBIT #########################################################
###########################################################################

# Create simulation object and propagate dynamics.
dynamics_simulator_perturbed = simulator.create_dynamics_simulator(
    bodies, propagator_settings_perturbed
)

# Retrieve all data produced by simulation
propagation_result_perturbed = dynamics_simulator_perturbed.propagation_results

# Extract numerical solution for states and dependent 
state_history_perturbed = propagation_result_perturbed.state_history
state_array_perturbed = result2array(state_history_perturbed)
dependent_variables_perturbed = propagation_result_perturbed.dependent_variable_history


###########################################################################
# SAVE RESULTS ############################################################
###########################################################################
results_directory = "./results"

save2txt(
    solution=state_history_perturbed, filename="JUICEPropagationHistory_Q4_perturbed.dat", directory=results_directory
)

save2txt(
    solution=dependent_variables_perturbed,
    filename="JUICEPropagationHistory_DependentVariables_Q4_perturbed.dat",
    directory=results_directory,
)


###########################################################################
# NOW UNPERTURBED CASE ####################################################
###########################################################################

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle_unperturbed = dict(Ganymede=[propagation_setup.acceleration.point_mass_gravity()])


# Create global accelerations dictionary.
acceleration_settings_unperturbed = {"JUICE": acceleration_settings_on_vehicle_unperturbed}

# Create acceleration models.
acceleration_models_unperturbed = propagation_setup.create_acceleration_models(
    bodies, 
    acceleration_settings_unperturbed, 
    bodies_to_propagate, 
    central_bodies
)

propagator_settings_unperturbed = propagation_setup.propagator.translational(
    central_bodies,
    acceleration_models_unperturbed,
    bodies_to_propagate,
    system_initial_state,
    simulation_start_epoch,
    integrator_settings,
    termination_settings,
    output_variables=dependent_variables_to_save,
)

propagator_settings_unperturbed.print_settings.print_initial_and_final_conditions = True

# Create simulation object and propagate dynamics.
dynamics_simulator_unperturbed = simulator.create_dynamics_simulator(
    bodies, propagator_settings_unperturbed
)

# Retrieve all data produced by simulation
propagation_result_unperturbed = dynamics_simulator_unperturbed.propagation_results

# Extract numerical solution for states and dependent 
state_history_unperturbed = propagation_result_unperturbed.state_history
state_array_unperturbed = result2array(state_history_unperturbed)
dependent_variables_unperturbed = propagation_result_unperturbed.dependent_variable_history


###########################################################################
# SAVE RESULTS ############################################################
###########################################################################
results_directory = "./results"

save2txt(
    solution=state_history_unperturbed, filename="JUICEPropagationHistory_Q4_unperturbed.dat", directory=results_directory
)

save2txt(
    solution=dependent_variables_unperturbed,
    filename="JUICEPropagationHistory_DependentVariables_Q4_unperturbed.dat",
    directory=results_directory,
)

# ###########################################################################
# # WRITE TO RESULTS FILE ###################################################
# ###########################################################################
# os.makedirs('documents_deliverable', exist_ok=True)
# results_path = Path("./documents_deliverable/cartesian_results_AE4868_2026_A1_6541356.txt")

# cartesian_nosrp = np.vstack(list(state_history_nosrp.values()))[sorted_indices]
# final_time = time_array[-1]
# final_cartesian_state_nosrp = cartesian_nosrp[-1, :]

# try:
#     with open(results_path, 'r') as file:
#         lines = file.readlines()
# except FileNotFoundError:
#     lines = []

# line_to_replace = 4  # (change between questions)
# while len(lines) <= line_to_replace:
#     lines.append('\n')

# output_line = f"{final_time:.16e} {final_cartesian_state_nosrp[0]:.16e} {final_cartesian_state_nosrp[1]:.16e} {final_cartesian_state_nosrp[2]:.16e} {final_cartesian_state_nosrp[3]:.16e} {final_cartesian_state_nosrp[4]:.16e} {final_cartesian_state_nosrp[5]:.16e}\n"
# lines[line_to_replace] = output_line

# with open(results_path, 'w') as file:
#     file.writelines(lines)