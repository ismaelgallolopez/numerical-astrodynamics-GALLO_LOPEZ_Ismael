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
from matplotlib import pyplot as plt
from tudatpy import constants
from tudatpy.data import save2txt
from tudatpy.interface import spice
from tudatpy.dynamics import environment_setup, propagation_setup, simulator
from tudatpy.astro import element_conversion

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
global_frame_origin = "SSB"
global_frame_orientation = "ECLIPJ2000"
body_settings = environment_setup.get_default_body_settings(
    bodies_to_create, global_frame_origin, global_frame_orientation
)

body_settings.get("Ganymede").atmosphere_settings = environment_setup.atmosphere.exponential(density_scale_height, density_at_zero_altitude)

occulting_bodies_dict = dict()
occulting_bodies_dict["Sun"] = ["Ganymede"]
vehicle_target_settings = environment_setup.radiation_pressure.cannonball_radiation_target(ref_area_juice,rad_pres_coeff_juice,occulting_bodies_dict)

###########################################################################
# CREATE VEHICLE ##########################################################
###########################################################################

body_settings.add_empty_settings("JUICE")
body_settings.get( "JUICE" ).radiation_pressure_target_settings = vehicle_target_settings

# Create environment
bodies = environment_setup.create_system_of_bodies(body_settings)
bodies.get_body("JUICE").mass = mass_juice

# drag settings 
aero_coefficient_settings = environment_setup.aerodynamic_coefficients.constant(ref_area_juice, [drag_coeff_juice, 0, 0])
environment_setup.add_aerodynamic_coefficient_interface(bodies, "JUICE", aero_coefficient_settings)

###########################################################################
# CREATE ACCELERATIONS ####################################################
###########################################################################

# Define bodies that are propagated, and their central bodies of propagation.
bodies_to_propagate = ["JUICE"]
central_bodies = ["Ganymede"]

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle = dict(Ganymede=[propagation_setup.acceleration.spherical_harmonic_gravity(2,2),
                                                  propagation_setup.acceleration.aerodynamic()],
                                        Jupiter=[propagation_setup.acceleration.spherical_harmonic_gravity(4,0)],
                                        Sun=[propagation_setup.acceleration.point_mass_gravity(),
                                             propagation_setup.acceleration.radiation_pressure()], # CHECK 
                                        Saturn=[propagation_setup.acceleration.point_mass_gravity()],
                                        Europa=[propagation_setup.acceleration.point_mass_gravity()],
                                        Io=[propagation_setup.acceleration.point_mass_gravity()],
                                        Callisto=[propagation_setup.acceleration.point_mass_gravity()],)

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
# Get Ganymede gravitational parameter
ganymede_grav_param = bodies.get("Ganymede").gravitational_parameter
# print(ganymede_grav_param) # debugging
# Transform initial state to keplerian
system_initial_state_keplerian = element_conversion.cartesian_to_keplerian(system_initial_state, ganymede_grav_param)

# print(system_initial_state) # debugging

# Define required outputs
dependent_variables_to_save = [
    propagation_setup.dependent_variable.keplerian_state( "JUICE", "Ganymede" ),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.spherical_harmonic_gravity_type , "JUICE", "Ganymede"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Io"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Sun"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.radiation_pressure_type , "JUICE", "Sun"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.aerodynamic_type , "JUICE", "Ganymede" )
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
# ANALYTICAL PROPAGATION ##################################################
###########################################################################

time = dependent_variables.keys()
time_array = np.array(list(time))
time_days = [
    t / constants.JULIAN_DAY - simulation_start_epoch / constants.JULIAN_DAY
    for t in time
]
# print(type(time)) # debugging
# print(f"Start epoch: {simulation_start_epoch} s") # debugging
# print(list(time)[0] - simulation_start_epoch) # debugging

sma = system_initial_state_keplerian[0]
eccentricity = system_initial_state_keplerian[1]

initial_true_anomaly = system_initial_state_keplerian[5]
initial_eccentric_anomaly = 2* np.arctan( ((1-eccentricity)/(1+eccentricity))**0.5 * np.tan(initial_true_anomaly/2) )
initial_mean_anomaly = initial_eccentric_anomaly - eccentricity*np.sin(initial_eccentric_anomaly)
# print(eccentricity) # debugging

# calculation of the mean anomaly through the mean motion
mean_motion = (ganymede_grav_param/sma**3)**0.5
mean_anomaly = initial_mean_anomaly + mean_motion * (time_array - simulation_start_epoch)

# solver for the Eccentric anomaly
def solve_E(M):
    func = lambda E: E - eccentricity * np.sin(E) - M
    return fsolve(func, M)[0]

solve_kepler_vectorized = np.vectorize(solve_E)
eccentric_anomaly = solve_kepler_vectorized(mean_anomaly)

# true anomaly from the eccentric anomaly
true_anomaly = 2* np.arctan( ((1+eccentricity)/(1-eccentricity))**0.5 * np.tan(eccentric_anomaly/2) ) # [-pi, pi]

# print(f'Maximum true anomaly {max(true_anomaly) / np.pi} pi') # debugging
# print(f'Minimum true anomaly {min(true_anomaly) / np.pi} pi') # debugging


###########################################################################
# SAVE RESULTS ############################################################
###########################################################################
results_directory = "./results"

save2txt(
    solution=state_history, filename="JUICEPropagationHistory_Q1.dat", directory=results_directory
)

save2txt(
    solution=dependent_variables,
    filename="JUICEPropagationHistory_DependentVariables_Q1.dat",
    directory=results_directory,
)

###########################################################################
# PLOT RESULTS ############################################################
###########################################################################

# Extract time and Kepler elements from dependent variables
kepler_elements = np.vstack(list(dependent_variables.values()))
# print(kepler_elements.shape)

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

# 1. Get the initial Kepler elements (at t0)pyt
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
fig, axs = plt.subplots(3, 2, figsize=(10, 8))
# fig.suptitle(f'Change in JUICE Kepler Elements w.r.t $t_0$ (Frame: {global_frame_orientation})', fontsize=16)

# Flatten the axes array for easy iteration (0 to 5)
axs_flat = axs.flatten()

for i in range(6):
    axs_flat[i].plot(time_days, delta_kepler[:, i])
    axs_flat[i].set_title(titles[i], fontsize=14)
    axs_flat[i].set_xlabel('Time since $t_0$ [days]', fontsize=12)
    axs_flat[i].set_ylabel(y_labels[i], fontsize=12)
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

# ###########################################################################
# # PLOT COMPARISON #########################################################
# ###########################################################################

# # KEPLERIAN ERROR ANALYSIS

# # 1. Construct the Analytical Kepler Elements Array
# # a, e, i, omega, Omega are constant in the unperturbed analytical solution
# # We use the initial state for the first 5 elements
# analytical_kepler = np.zeros_like(kepler_elements)
# for i in range(5):
#     analytical_kepler[:, i] = initial_state[i]

# analytical_kepler[:, 5] = true_anomaly


# # print(np.unwrap(true_anomaly)[1000:1500]) # debugging
# # print(max(analytical_kepler[:, 5]) / np.pi) # debugging
# # print(min(analytical_kepler[:, 5]) / np.pi) # debugging
# # print(max(kepler_elements[:, 5]) / np.pi) # debugging
# # print(min(kepler_elements[:, 5]) / np.pi) # debugging

# # # debugging
# # plt.plot(true_anomaly, label='Wrapped')
# # plt.plot(np.unwrap(true_anomaly), label='Unwrapped')
# # plt.plot(kepler_elements[:, 5], label='Numerical wrapped')
# # plt.plot(np.unwrap(kepler_elements[:, 5]), label='Numerical unwrappped')
# # plt.legend()
# # plt.show()

# # The 6th element is your analytically propagated true anomaly
# analytical_true_anom_unwrap = np.unwrap(true_anomaly)
# # also unwrap the numerical propagated true anomaly
# true_anom_unwrap = np.unwrap(kepler_elements[:, 5])

# # 2. Calculate the Error (Numerical - Analytical)
# kepler_error = kepler_elements - analytical_kepler
# kepler_error[:, 5] = true_anom_unwrap - analytical_true_anom_unwrap

# # 3. Convert angular errors (indices 2 to 5) from Radians to Degrees
# kepler_error[:, 2:6] = np.rad2deg(kepler_error[:, 2:6])

# # 4. Define labels for the error plot
# error_y_labels = [
#     "Error in $a$ [m]",
#     "Error in $e$ [-]",
#     "Error in $i$ [deg]",
#     "Error in $\omega$ [deg]",
#     "Error in $\Omega$ [deg]",
#     "Error in $\\theta$ [deg]"
# ]

# # 5. Generate the comparison plot
# fig_err, axs_err = plt.subplots(3, 2, figsize=(12, 10))
# # fig_err.suptitle('Numerical Integration Error vs Analytical Solution (Keplerian)', fontsize=16)

# axs_err_flat = axs_err.flatten()

# for i in range(6):
#     axs_err_flat[i].plot(time_days, kepler_error[:, i], color='tab:red')
#     axs_err_flat[i].set_title(titles[i], fontsize=14)
#     axs_err_flat[i].set_xlabel('Time since $t_0$ [days]', fontsize=12)
#     axs_err_flat[i].set_ylabel(error_y_labels[i], fontsize=12)
#     axs_err_flat[i].grid(True)
    
#     # Use scientific notation for the y-axis if the errors are very small
#     axs_err_flat[i].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

# # Improve layout spacing
# plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# # 6. Save the figure
# error_output_path = os.path.join(output_dir, "keplerian_integration_error_q1.pdf")
# plt.savefig(error_output_path)
# print(f"Comparison plot saved to: {error_output_path}")

# plt.close()


# # CARTESIAN ERROR ANALYSIS

# # 1. coordinate transform from keplerian to cartesian for the analytical solution
# analytical_cartesian = np.zeros((len(time_days), 6))
# for i in range(len(time_days)):
#     analytical_cartesian[i,:] = element_conversion.keplerian_to_cartesian(analytical_kepler[i,:], ganymede_grav_param)

# # 2. Extract the numerical Cartesian states
# # Extract states from state_history, ensuring it is sorted by time to match the analytical arrays
# numerical_cartesian = np.vstack(list(state_history.values()))[sorted_indices]

# # 3. Calculate the Error (Numerical - Analytical)
# cartesian_error = numerical_cartesian - analytical_cartesian

# # 4. Define labels for the error plot
# cartesian_titles = [
#     "Error in Position $X$", "Error in Position $Y$", "Error in Position $Z$",
#     "Error in Velocity $v_x$", "Error in Velocity $v_y$", "Error in Velocity $v_z$"
# ]

# cartesian_y_labels = [
#     "$\Delta X$ [m]", "$\Delta Y$ [m]", "$\Delta Z$ [m]",
#     "$\Delta v_x$ [m/s]", "$\Delta v_y$ [m/s]", "$\Delta v_z$ [m/s]"
# ]

# # 5. Generate the comparison plot
# fig_cart, axs_cart = plt.subplots(3, 2, figsize=(12, 10))
# # fig_cart.suptitle('Numerical Integration Error vs Analytical Solution (Cartesian)', fontsize=16)

# axs_cart_flat = axs_cart.flatten()

# for i in range(6):
#     axs_cart_flat[i].plot(time_days, cartesian_error[:, i], color='tab:green')
#     axs_cart_flat[i].set_title(cartesian_titles[i], fontsize=14)
#     axs_cart_flat[i].set_xlabel('Time since $t_0$ [days]', fontsize=12)
#     axs_cart_flat[i].set_ylabel(cartesian_y_labels[i], fontsize=12)
#     axs_cart_flat[i].grid(True)
    
#     # Use scientific notation for the y-axis if the errors are very small
#     axs_cart_flat[i].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

# # Improve layout spacing
# plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# # 6. Save the figure
# cartesian_output_path = os.path.join(output_dir, "cartesian_integration_error_q1.pdf")
# plt.savefig(cartesian_output_path)
# print(f"Cartesian comparison plot saved to: {cartesian_output_path}")

# plt.close()

# # MAGNITUDE OF CARTESIAN ERROR ANALYSIS

# # 1. Calculate the magnitude (Euclidean norm) of the error at each time step
# # axis=1 ensures the norm is calculated across the columns for each row (epoch)
# pos_error_mag = np.linalg.norm(cartesian_error[:, 0:3], axis=1)
# vel_error_mag = np.linalg.norm(cartesian_error[:, 3:6], axis=1)

# # 2. Generate the plot
# fig_mag, axs_mag = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
# fig_mag.suptitle('Magnitude of Cartesian Integration Error', fontsize=16)

# # Position Error Magnitude
# axs_mag[0].plot(time_days, pos_error_mag, color='tab:orange', linewidth=2)
# axs_mag[0].set_title('Position Error Magnitude (RSS)', fontsize=14)
# axs_mag[0].set_ylabel('$\|\Delta \mathbf{r}\|$ [m]', fontsize=12)
# axs_mag[0].grid(True)
# axs_mag[0].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

# # Velocity Error Magnitude
# axs_mag[1].plot(time_days, vel_error_mag, color='tab:purple', linewidth=2)
# axs_mag[1].set_title('Velocity Error Magnitude (RSS)', fontsize=14)
# axs_mag[1].set_xlabel('Time since $t_0$ [days]', fontsize=12)
# axs_mag[1].set_ylabel('$\|\Delta \mathbf{v}\|$ [m/s]', fontsize=12)
# axs_mag[1].grid(True)
# axs_mag[1].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

# # Improve layout spacing
# plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# # 3. Save the figure
# mag_output_path = os.path.join(output_dir, "magnitude_integration_error_q1.pdf")
# plt.savefig(mag_output_path)
# print(f"Error magnitude plot saved to: {mag_output_path}")

# plt.close()


# ###########################################################################
# # WRITE TO RESULTS FILE ###################################################
# ###########################################################################
# os.makedirs('documents_deliverable', exist_ok=True)
# results_path = Path("./documents_deliverable/cartesian_results_AE4868_2026_A1_6541356.txt")

# final_time = time_array[-1]
# final_cartesian_state = numerical_cartesian[-1, :]

# try:
#     with open(results_path, 'r') as file:
#         lines = file.readlines()
# except FileNotFoundError:
#     lines = []

# line_to_replace = 1  # (change between questions)
# while len(lines) <= line_to_replace:
#     lines.append('\n')

# output_line = f"{final_time:.16e} {final_cartesian_state[0]:.16e} {final_cartesian_state[1]:.16e} {final_cartesian_state[2]:.16e} {final_cartesian_state[3]:.16e} {final_cartesian_state[4]:.16e} {final_cartesian_state[5]:.16e}\n"
# lines[line_to_replace] = output_line

# with open(results_path, 'w') as file:
#     file.writelines(lines)

