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
from tudatpy.astro import element_conversion, frame_conversion

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
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.aerodynamic_type , "JUICE", "Ganymede" ),
    propagation_setup.dependent_variable.dynamic_pressure("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.aerodynamic_force_coefficients("JUICE", "Ganymede"), # for doing sanity check on C_D
    propagation_setup.dependent_variable.airspeed("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.density("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.radiation_pressure_coefficient("JUICE", "Sun"), # sanity check
    propagation_setup.dependent_variable.body_mass("JUICE"), # sanity check
    propagation_setup.dependent_variable.relative_position("JUICE", "Sun"),
    propagation_setup.dependent_variable.tnw_to_inertial_rotation_matrix("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.body_fixed_airspeed_velocity("JUICE", "Ganymede")
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
results_directory = "./results"

save2txt(
    solution=state_history, filename="JUICEPropagationHistory_Q3.dat", directory=results_directory
)

save2txt(
    solution=dependent_variables,
    filename="JUICEPropagationHistory_DependentVariables_Q3.dat",
    directory=results_directory,
)

###########################################################################
# PLOT RESULTS ############################################################
###########################################################################

# Extract time and Kepler elements from dependent variables
kepler_elements = np.vstack(list(dependent_variables.values()))
# print(kepler_elements.shape) # debugging

# Ensure the 'figures' directory exists
output_dir = os.path.join(current_directory, "figures")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Extract time and Kepler elements from dependent variables
# Note: Ensure the dictionary is sorted by time before stacking
sorted_indices = np.argsort(list(dependent_variables.keys()))
# kepler_elements = np.vstack(list(dependent_variables.values()))[sorted_indices] # debugging

# Extract time arrays
time = dependent_variables.keys()
# print(time) # debugging
time_array = np.array(list(time))
time_days = [
    t / constants.JULIAN_DAY - simulation_start_epoch / constants.JULIAN_DAY
    for t in time
]

# Extract the numerical Cartesian states
numerical_cartesian = np.vstack(list(state_history.values()))[sorted_indices]

# ###########################################################################
# # PLOT THIRD-BODY ACCELERATION NORMS ######################################
# ###########################################################################

# # Ensure we have the full dependent variables matrix sorted by time
# dep_vars_matrix = np.vstack(list(dependent_variables.values()))[sorted_indices]

# # Extract the 3D acceleration vectors based on the dependent_variables_to_save order
# accel_io_vector = dep_vars_matrix[:, 9:12]
# accel_sun_vector = dep_vars_matrix[:, 12:15]

# # Calculate the magnitudes (Euclidean norm) at each time step
# norm_accel_io = np.linalg.norm(accel_io_vector, axis=1)
# norm_accel_sun = np.linalg.norm(accel_sun_vector, axis=1)

# # Generate the plot
# fig_accel, ax_accel = plt.subplots(figsize=(10, 6))

# # Plotting on a logarithmic y-axis
# ax_accel.semilogy(time_days, norm_accel_sun, label='Sun Third-Body Gravity', color='tab:orange', linewidth=2)
# ax_accel.semilogy(time_days, norm_accel_io, label='Io Third-Body Gravity', color='tab:purple', linewidth=2)

# ax_accel.set_title('Magnitudes of Third-Body Gravitational Accelerations on JUICE', fontsize=14, fontweight='bold')
# ax_accel.set_xlabel('Time since $t_0$ [days]', fontsize=12)
# ax_accel.set_ylabel('Acceleration Norm [$\mathrm{m/s}^2$]', fontsize=12)

# # Grid formatting for log scale
# ax_accel.grid(True, which="major", linestyle="-", alpha=0.6)
# ax_accel.grid(True, which="minor", linestyle="--", alpha=0.3)
# ax_accel.legend(fontsize=12)

# # Improve layout spacing
# plt.tight_layout()

# # Save the figure
# accel_output_path = os.path.join(output_dir, "third_body_accelerations_q2.pdf")
# plt.savefig(accel_output_path)
# print(f"Acceleration norms plot saved to: {accel_output_path}")

# plt.close()

# ###########################################################################
# # FFT ANALYSIS FOR PERIOD OF MAXIMUM VARIATION ############################
# ###########################################################################

# norm_accel_io_fft = norm_accel_io - np.mean(norm_accel_io)
# norm_accel_sun_fft = norm_accel_sun - np.mean(norm_accel_sun)

# number_of_points = len(time_array)
# # timestep = fixed_step_size  # seconds

# # print(norm_accel_io_fft.mean())  # debugging
# # print(norm_accel_io_fft.shape)  # debugging

# # Source - https://stackoverflow.com/a/49545394
# # Posted by francis, modified by community. See post 'Timeline' for change history
# # Retrieved 2026-02-21, License - CC BY-SA 4.0

# fft_accel_io = fft(norm_accel_io_fft)
# fft_accel_sun = fft(norm_accel_sun_fft)
# # print(fft_accel_io) # debugging

# def abs2(x):
#     return x.real**2 + x.imag**2

# fft_accel_io_ampl = abs2(fft_accel_io)
# fft_accel_sun_ampl = abs2(fft_accel_sun)

# pos_max_accel_io_ampl = np.argmax(fft_accel_io_ampl)
# pos_max_accel_sun_ampl = np.argmax(fft_accel_sun_ampl)

# # print(pos_max_accel_io_ampl) # debugging
# # print(len(norm_accel_io_fft)) # debugging


# # print(fft_accel_io_ampl[pos_max_accel_io_ampl]) # debugging
# # print(np.max(fft_accel_io_ampl)) # debugging


# freq = fftfreq(number_of_points, d=fixed_step_size)
# # print(freq.shape) # debugging
# # print(freq[pos_max_accel_io_ampl]) # debugging

# freq_max_accel_io_ampl = freq[pos_max_accel_io_ampl]
# period_max_accel_io_ampl = 1/freq_max_accel_io_ampl
# print(f"The period of the variation of Io's acceleration is {period_max_accel_io_ampl/3600:.2f} hours")

# freq_max_accel_sun_ampl = freq[pos_max_accel_sun_ampl]
# period_max_accel_sun_ampl = 1/freq_max_accel_sun_ampl
# print(f"The period of the variation of Sun's acceleration is {period_max_accel_sun_ampl/3600:.2f} hours")

# # ANALYSIS AS FUNCTION OF RELEVANT PERIODS

# # JUICE period
# sma = system_initial_state_keplerian[0]
# T_JUICE = 2 * np.pi * (sma**3 / ganymede_grav_param)**0.5
# # print("T_JUICE = ", T_JUICE, " s") # debugging
 
# T_ganymede = 7.15455296 * constants.JULIAN_DAY # https://en.wikipedia.org/wiki/Ganymede_(moon)
# T_io = 1.769137786 * constants.JULIAN_DAY # https://en.wikipedia.org/wiki/Io_(moon) 
# T_jupiter = 11.862 * constants.JULIAN_YEAR # https://en.wikipedia.org/wiki/Jupiter

# print("\nRatios of period of maximum variation of acceletation by IO to relevant periods: ")
# print(f"T_max_io / T_JUICE: {period_max_accel_io_ampl/T_JUICE:.2f} (Inverse: {T_JUICE/period_max_accel_io_ampl:.2f})")
# print(f"T_max_io / T_io: {period_max_accel_io_ampl/T_io:.2f} (Inverse: {T_io/period_max_accel_io_ampl:.2f})")
# print(f"T_max_io / T_ganymede: {period_max_accel_io_ampl/T_ganymede:.2f} (Inverse: {T_ganymede/period_max_accel_io_ampl:.2f})")
# print(f"T_max_io / T_jupiter: {period_max_accel_io_ampl/T_jupiter:.2f} (Inverse: {T_jupiter/period_max_accel_io_ampl:.2f})")

# print("\nRatios of period of maximum variation of acceletation by Sun to relevant periods: ")
# print(f"T_max_sun / T_JUICE: {period_max_accel_sun_ampl/T_JUICE:.2f} (Inverse: {T_JUICE/period_max_accel_sun_ampl:.2f})")
# print(f"T_max_sun / T_io: {period_max_accel_sun_ampl/T_io:.2f} (Inverse: {T_io/period_max_accel_sun_ampl:.2f})")
# print(f"T_max_sun / T_ganymede: {period_max_accel_sun_ampl/T_ganymede:.2f} (Inverse: {T_ganymede/period_max_accel_sun_ampl:.2f})")
# print(f"T_max_sun / T_jupiter: {period_max_accel_sun_ampl/T_jupiter:.2f} (Inverse: {T_jupiter/period_max_accel_sun_ampl:.2f})")

# ###########################################################################
# # PLOT ZOOMED ACCELERATIONS WITH SUPERIMPOSED PERIODS #####################
# ###########################################################################

# # Convert the calculated periods from seconds to days for the x-axis
# T_io_days = period_max_accel_io_ampl / (24 * 3600)
# T_sun_days = period_max_accel_sun_ampl / (24 * 3600)

# # Convert time_days list to a numpy array for easy boolean masking
# time_days_arr = np.array(time_days)

# # Create a 2-panel figure
# fig_zoom, axs_zoom = plt.subplots(2, 1, figsize=(12, 10))

# # --- PANEL 1: IO ---
# # Define a subset window (e.g., 5 times the dominant period)
# num_periods_to_plot_io = 5
# window_io = num_periods_to_plot_io * T_io_days
# mask_io = time_days_arr <= window_io

# axs_zoom[0].plot(time_days_arr[mask_io], norm_accel_io[mask_io], color='tab:purple', linewidth=2)
# axs_zoom[0].set_title(f"Io Third-Body Acceleration (First {window_io:.2f} Days)\nSuperimposed Period: {T_io_days:.2f} Days", fontsize=14, fontweight='bold')
# axs_zoom[0].set_ylabel('Acceleration [$\mathrm{m/s}^2$]', fontsize=12)
# axs_zoom[0].grid(True, alpha=0.6)

# # Superimpose the period with vertical lines
# for i in range(1, num_periods_to_plot_io + 1):
#     axs_zoom[0].axvline(x=i * T_io_days, color='red', linestyle='--', linewidth=1.5, alpha=0.8, 
#                         label='FFT Period' if i == 1 else "")
# axs_zoom[0].legend(loc="upper right")


# # --- PANEL 2: SUN ---
# # Define a subset window (e.g., 5 times the dominant period)
# num_periods_to_plot_sun = 5
# window_sun = num_periods_to_plot_sun * T_sun_days
# mask_sun = time_days_arr <= window_sun

# axs_zoom[1].plot(time_days_arr[mask_sun], norm_accel_sun[mask_sun], color='tab:orange', linewidth=2)
# axs_zoom[1].set_title(f"Sun Third-Body Acceleration (First {window_sun:.2f} Days)\nSuperimposed Period: {T_sun_days:.2f} Days", fontsize=14, fontweight='bold')
# axs_zoom[1].set_xlabel('Time since $t_0$ [days]', fontsize=12)
# axs_zoom[1].set_ylabel('Acceleration [$\mathrm{m/s}^2$]', fontsize=12)
# axs_zoom[1].grid(True, alpha=0.6)

# # Superimpose the period with vertical lines
# for i in range(1, num_periods_to_plot_sun + 1):
#     axs_zoom[1].axvline(x=i * T_sun_days, color='red', linestyle='--', linewidth=1.5, alpha=0.8,
#                         label='FFT Period' if i == 1 else "")
# axs_zoom[1].legend(loc="upper right")

# # Improve layout
# plt.tight_layout()

# # Save the figure
# zoom_output_path = os.path.join(output_dir, "zoomed_accelerations_periods_q2.pdf")
# plt.savefig(zoom_output_path)
# print(f"Zoomed acceleration period plot saved to: {zoom_output_path}")

# plt.close()

###########################################################################
# VALIDATING ACCELERATIONS ################################################
###########################################################################

c = 299792458 # m/s https://en.wikipedia.org/wiki/Speed_of_light
P = 3.828e26 # W https://en.wikipedia.org/wiki/Solar_luminosity

# extraction of dependent variables 
dep_vars = propagation_results.dependent_variable_history
dep_vars_matrix = np.vstack(list(dependent_variables.values()))[sorted_indices]
dep_vars_ids = propagation_results.dependent_variable_ids

print("Dependent variable IDs: ", dep_vars_ids) # debugging

if not len(dep_vars[simulation_start_epoch]) == 44: # debugging in case that more dependent variables are added
    raise ValueError(f"Expected 44 dependent variables, but got {len(dep_vars[simulation_start_epoch])}") # debugging in case that more dependent variables are added

# print(dep_vars_matrix) # debugging

mass_sanity_check = dep_vars_matrix[:,28]
print(f"Mass sanity check: {mass_sanity_check[0]} kg") # debugging
# aerodynamic_coeffs = dep_vars_matrix[:, 22:25] # only for sanity check of drag
# print(aerodynamic_coeffs[0]) # print first aerodynamic coefficient

dynamic_pressure = dep_vars_matrix[:, 21]
density = dep_vars_matrix[:, 26]
sun_juice_position = dep_vars_matrix[:, 29:32]
airspeed = dep_vars_matrix[:, 25]
airspeed_vector = dep_vars_matrix[:, 41:44]

# sanity checks
if not np.allclose(dynamic_pressure, 0.5 * density * airspeed**2):
    raise ValueError("Dynamic pressure does not match ") # sanity check
radiation_pressure_coeff_sanity = dep_vars_matrix[:, 27]
if not np.allclose(radiation_pressure_coeff_sanity, rad_pres_coeff_juice):
    raise ValueError("Radiation pressure coefficient does not match the expected value") # sanity check

# calculation of accelerations for validation
accel_aerodynamic_manual_mag = dynamic_pressure * ref_area_juice * drag_coeff_juice / mass_juice
airspeed_norm = np.linalg.norm(airspeed_vector, axis=1)[:, np.newaxis]
airspeed_unitary_vector = airspeed_vector / airspeed_norm
accel_aerodynamic_manual = -accel_aerodynamic_manual_mag[:, np.newaxis] * airspeed_unitary_vector

sun_juice_position_mag = np.linalg.norm(sun_juice_position, axis=1)
# print(sun_juice_position_mag.shape) # debugging
accel_radiation_pressure_manual = (P / (4 * np.pi * c)) * (rad_pres_coeff_juice * ref_area_juice / mass_juice) * sun_juice_position / sun_juice_position_mag[:, np.newaxis]**3
# print(accel_radiation_pressure_manual.shape) # debugging
accel_radiation_pressure_manual_mag = np.linalg.norm(accel_radiation_pressure_manual, axis=1)
# print(accel_radiation_pressure_manual_mag) # debugging

# retrieving of accelerations from simulations
accel_aerodynamic_simulation = dep_vars_matrix[:, 15:18]
accel_aerodynamic_simulation_mag = np.linalg.norm(accel_aerodynamic_simulation, axis=1)
# print(accel_aerodynamic_simulation_mag) # debugging

accel_radiation_pressure_simulation = dep_vars_matrix[:, 18:21]
accel_radiation_pressure_simulation_mag = np.linalg.norm(accel_radiation_pressure_simulation, axis=1)
# print(accel_radiation_pressure_simulation_mag) # debugging

###########################################################################
# PLOT ACCELERATION VALIDATION ############################################
###########################################################################

# Correct the manual aerodynamic magnitude to be strictly positive for comparison
accel_aero_manual_mag_abs = np.abs(accel_aerodynamic_manual_mag)

# -------------------------------------------------------------------------
# 1. Aerodynamic Magnitude Comparison
# -------------------------------------------------------------------------
fig_aero, ax_aero = plt.subplots(figsize=(10, 6))
ax_aero.plot(time_days, accel_aerodynamic_simulation_mag, label='Tudat Simulation', color='tab:blue', linewidth=2)
ax_aero.plot(time_days, accel_aero_manual_mag_abs, label='Manual Analytical', color='red', linestyle='--', linewidth=2)

ax_aero.set_title('Aerodynamic Acceleration Magnitude Validation', fontsize=14, fontweight='bold')
ax_aero.set_xlabel('Time since $t_0$ [days]', fontsize=12)
ax_aero.set_ylabel(r'Magnitude [$\mathrm{m/s}^2$]', fontsize=12)
ax_aero.grid(True, alpha=0.6)
ax_aero.legend(fontsize=12)

plt.tight_layout()
aero_val_path = os.path.join(output_dir, "validation_aero_mag_q3.pdf")
plt.savefig(aero_val_path)
print(f"Aerodynamic validation plot saved to: {aero_val_path}")
plt.close()

# -------------------------------------------------------------------------
# 2. Radiation Pressure Magnitude Comparison
# -------------------------------------------------------------------------
fig_srp_mag, ax_srp_mag = plt.subplots(figsize=(10, 6))
ax_srp_mag.plot(time_days, accel_radiation_pressure_simulation_mag, label='Tudat Simulation', color='tab:orange', linewidth=2)
ax_srp_mag.plot(time_days, accel_radiation_pressure_manual_mag, label='Manual Analytical', color='black', linestyle='--', linewidth=2)

ax_srp_mag.set_title('Solar Radiation Pressure Magnitude Validation', fontsize=14, fontweight='bold')
ax_srp_mag.set_xlabel('Time since $t_0$ [days]', fontsize=12)
ax_srp_mag.set_ylabel(r'Magnitude [$\mathrm{m/s}^2$]', fontsize=12)
ax_srp_mag.grid(True, alpha=0.6)
ax_srp_mag.legend(fontsize=12)

plt.tight_layout()
srp_mag_val_path = os.path.join(output_dir, "validation_srp_mag_q3.pdf")
plt.savefig(srp_mag_val_path)
print(f"SRP magnitude validation plot saved to: {srp_mag_val_path}")
plt.close()

# -------------------------------------------------------------------------
# 3. Radiation Pressure Vector Comparison
# -------------------------------------------------------------------------
fig_srp_vec, axs_srp_vec = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
fig_srp_vec.suptitle('Solar Radiation Pressure Vector Validation', fontsize=16, fontweight='bold', y=0.96)

components = ['X', 'Y', 'Z']
colors = ['tab:red', 'tab:green', 'tab:purple']

for i in range(3):
    # Plot numerical simulation as solid thick lines
    axs_srp_vec[i].plot(time_days, accel_radiation_pressure_simulation[:, i], label='Tudat Simulation', color=colors[i], linewidth=2)
    # Plot manual calculation as dashed black lines over the top
    axs_srp_vec[i].plot(time_days, accel_radiation_pressure_manual[:, i], label='Manual Analytical', color='black', linestyle='--', linewidth=1.5)
    
    axs_srp_vec[i].set_ylabel(components[i] + ' Component [m s^-2]', fontsize=12)
    axs_srp_vec[i].grid(True, alpha=0.6)
    axs_srp_vec[i].legend(loc='upper right', fontsize=10)

axs_srp_vec[-1].set_xlabel('Time since $t_0$ [days]', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
srp_vec_val_path = os.path.join(output_dir, "validation_srp_vector_q3.pdf")
plt.savefig(srp_vec_val_path)
print(f"SRP vector validation plot saved to: {srp_vec_val_path}")
plt.close()

# -------------------------------------------------------------------------
# 4. Aerodynamic acceleration Vector Comparison
# -------------------------------------------------------------------------
fig_aero_vec, axs_aero_vec = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
fig_aero_vec.suptitle('Aerodynamic Acceleration Vector Validation', fontsize=16, fontweight='bold', y=0.96)

components = ['X', 'Y', 'Z']
colors = ['tab:red', 'tab:green', 'tab:purple']

for i in range(3):
    # Plot numerical simulation as solid thick lines
    axs_aero_vec[i].plot(time_days, accel_aerodynamic_simulation[:, i], label='Tudat Simulation', color=colors[i], linewidth=2)
    # Plot manual calculation as dashed black lines over the top
    axs_aero_vec[i].plot(time_days, accel_aerodynamic_manual[:, i], label='Manual Analytical', color='black', linestyle='--', linewidth=1.5)
    
    axs_aero_vec[i].set_ylabel(components[i] + ' Component [m s^-2]', fontsize=12)
    axs_aero_vec[i].grid(True, alpha=0.6)
    axs_aero_vec[i].legend(loc='upper right', fontsize=10)

axs_aero_vec[-1].set_xlabel('Time since $t_0$ [days]', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
aero_vec_val_path = os.path.join(output_dir, "validation_aero_vector_q3.pdf")
plt.savefig(aero_vec_val_path)
print(f"Aerodynamic vector validation plot saved to: {aero_vec_val_path}")
plt.close()

###########################################################################
# RSW FRAME CONVERSION ####################################################
###########################################################################

# print(numerical_cartesian[0, :]) # debugging
# rotation_matrix = np.empty((len(numerical_cartesian), 3,3)) # debugging
# for i in range(len(numerical_cartesian)):
#     rotation_matrix[i] = frame_conversion.rsw_to_inertial_rotation_matrix(numerical_cartesian[i, :])

# print(rotation_matrix) # debugging

# construction of the rotation matrix
# print(dep_vars_matrix[:, 32:41]) # debugging
rotation_matrix_tnw_to_inertial = dep_vars_matrix[:, 32:41].reshape(-1, 3, 3) 
rotation_matrix_inertial_to_tnw = np.transpose(rotation_matrix_tnw_to_inertial, (0, 2, 1)) 
# print(rotation_matrix_inertial_to_tnw) # debugging

# rotating the accelerations to RSW
# print(accel_aerodynamic_simulation.shape, rotation_matrix_inertial_to_tnw.shape) # debugging
accel_aerodynamic_rsw = np.einsum('ijk, ik -> ij', rotation_matrix_inertial_to_tnw, accel_aerodynamic_simulation)
accel_radiation_pressure_rsw = np.einsum('ijk, ik -> ij', rotation_matrix_inertial_to_tnw, accel_radiation_pressure_simulation)

# print(accel_aerodynamic_rsw.shape) # debugging

###########################################################################
# PLOT ACCELERATIONS IN LOCAL FRAME (4 SEPARATE PLOTS) ####################
###########################################################################

# Component labels for the local frame (typically R, S, W or T, N, W)
local_components = ['Component 1 (Radial/Tangential)', 
                    'Component 2 (Transverse/Normal)', 
                    'Component 3 (Normal/Out-of-Plane)']

# -------------------------------------------------------------------------
# 1. Aerodynamic Acceleration Vector (Local Components)
# -------------------------------------------------------------------------
fig_aero_vec, axs_aero_vec = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
fig_aero_vec.suptitle('Aerodynamic Acceleration Components (Local Frame)', fontsize=16, fontweight='bold', y=0.96)

for i in range(3):
    axs_aero_vec[i].plot(time_days, accel_aerodynamic_rsw[:, i], color='tab:blue', linewidth=1.5)
    axs_aero_vec[i].set_ylabel(f'{local_components[i]}\n[m/s²]', fontsize=10)
    axs_aero_vec[i].grid(True, alpha=0.6)
    axs_aero_vec[i].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

axs_aero_vec[-1].set_xlabel('Time since t0 [days]', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
aero_vec_path = os.path.join(output_dir, "rsw_aero_acceleration_vector_local_q3.pdf")
plt.savefig(aero_vec_path)
print(f"Aerodynamic vector plot saved to: {aero_vec_path}")
plt.close()

# -------------------------------------------------------------------------
# 2. Aerodynamic Acceleration Magnitude
# -------------------------------------------------------------------------
fig_aero_mag, ax_aero_mag = plt.subplots(figsize=(10, 5))
ax_aero_mag.plot(time_days, accel_aerodynamic_simulation_mag, color='tab:blue', linewidth=2)

ax_aero_mag.set_title('Aerodynamic Acceleration Magnitude', fontsize=16, fontweight='bold')
ax_aero_mag.set_xlabel('Time since t0 [days]', fontsize=12)
ax_aero_mag.set_ylabel('Magnitude [m/s²]', fontsize=12)
ax_aero_mag.grid(True, alpha=0.6)
ax_aero_mag.ticklabel_format(style='sci', scilimits=(0,0), axis='y')

plt.tight_layout()
aero_mag_path = os.path.join(output_dir, "rsw_aero_acceleration_magnitude_q3.pdf")
plt.savefig(aero_mag_path)
print(f"Aerodynamic magnitude plot saved to: {aero_mag_path}")
plt.close()

# -------------------------------------------------------------------------
# 3. Solar Radiation Pressure Vector (Local Components)
# -------------------------------------------------------------------------
fig_srp_vec, axs_srp_vec = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
fig_srp_vec.suptitle('Solar Radiation Pressure Components (Local Frame)', fontsize=16, fontweight='bold', y=0.96)

for i in range(3):
    axs_srp_vec[i].plot(time_days, accel_radiation_pressure_rsw[:, i], color='tab:orange', linewidth=1.5)
    axs_srp_vec[i].set_ylabel(f'{local_components[i]}\n[m/s²]', fontsize=10)
    axs_srp_vec[i].grid(True, alpha=0.6)
    axs_srp_vec[i].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

axs_srp_vec[-1].set_xlabel('Time since t0 [days]', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
srp_vec_path = os.path.join(output_dir, "rsw_srp_acceleration_vector_local_q3.pdf")
plt.savefig(srp_vec_path)
print(f"SRP vector plot saved to: {srp_vec_path}")
plt.close()

# -------------------------------------------------------------------------
# 4. Solar Radiation Pressure Magnitude
# -------------------------------------------------------------------------
fig_srp_mag, ax_srp_mag = plt.subplots(figsize=(10, 5))
ax_srp_mag.plot(time_days, accel_radiation_pressure_simulation_mag, color='tab:orange', linewidth=2)

ax_srp_mag.set_title('Solar Radiation Pressure Magnitude', fontsize=16, fontweight='bold')
ax_srp_mag.set_xlabel('Time since t0 [days]', fontsize=12)
ax_srp_mag.set_ylabel('Magnitude [m/s²]', fontsize=12)
ax_srp_mag.grid(True, alpha=0.6)
ax_srp_mag.ticklabel_format(style='sci', scilimits=(0,0), axis='y')

plt.tight_layout()
srp_mag_path = os.path.join(output_dir, "rsw_srp_acceleration_magnitude_q3.pdf")
plt.savefig(srp_mag_path)
print(f"SRP magnitude plot saved to: {srp_mag_path}")
plt.close()

###########################################################################
# PPROPAGATION WITHOUT AERODYNAMIC ACCEL. #################################
###########################################################################

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle_noaero = dict(Ganymede=[propagation_setup.acceleration.spherical_harmonic_gravity(2,2)],
                                                #   propagation_setup.acceleration.aerodynamic()],
                                        Jupiter=[propagation_setup.acceleration.spherical_harmonic_gravity(4,0)],
                                        Sun=[propagation_setup.acceleration.point_mass_gravity(),
                                             propagation_setup.acceleration.radiation_pressure()], # CHECK 
                                        Saturn=[propagation_setup.acceleration.point_mass_gravity()],
                                        Europa=[propagation_setup.acceleration.point_mass_gravity()],
                                        Io=[propagation_setup.acceleration.point_mass_gravity()],
                                        Callisto=[propagation_setup.acceleration.point_mass_gravity()],)

# Create global accelerations dictionary.
acceleration_settings_noaero = {"JUICE": acceleration_settings_on_vehicle_noaero}

# Create acceleration models.
acceleration_models_noaero = propagation_setup.create_acceleration_models(
    bodies, acceleration_settings_noaero, bodies_to_propagate, central_bodies
)

###########################################################################
# CREATE PROPAGATION SETTINGS #############################################
###########################################################################

# # Define initial state.
# system_initial_state = spice.get_body_cartesian_state_at_epoch(
#     target_body_name="JUICE",
#     observer_body_name="Ganymede",
#     reference_frame_name="ECLIPJ2000",
#     aberration_corrections="NONE",
#     ephemeris_time=simulation_start_epoch,
# )
# Get Ganymede gravitational parameter
# ganymede_grav_param = bodies.get("Ganymede").gravitational_parameter
# print(ganymede_grav_param) # debugging
# Transform initial state to keplerian
# system_initial_state_keplerian = element_conversion.cartesian_to_keplerian(system_initial_state, ganymede_grav_param)

# print(system_initial_state) # debugging

# Define required outputs
dependent_variables_to_save = [
    propagation_setup.dependent_variable.keplerian_state( "JUICE", "Ganymede" ),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.spherical_harmonic_gravity_type , "JUICE", "Ganymede"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Io"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Sun"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.radiation_pressure_type , "JUICE", "Sun"),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.aerodynamic_type , "JUICE", "Ganymede" ),
    propagation_setup.dependent_variable.dynamic_pressure("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.aerodynamic_force_coefficients("JUICE", "Ganymede"), # for doing sanity check on C_D
    # propagation_setup.dependent_variable.airspeed("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.density("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.radiation_pressure_coefficient("JUICE", "Sun"), # sanity check
    propagation_setup.dependent_variable.body_mass("JUICE"), # sanity check
    propagation_setup.dependent_variable.relative_position("JUICE", "Sun"),
    propagation_setup.dependent_variable.tnw_to_inertial_rotation_matrix("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.body_fixed_airspeed_velocity("JUICE", "Ganymede")
]

# # Create numerical integrator settings.
# fixed_step_size = 10.0
# integrator_settings = propagation_setup.integrator.runge_kutta_fixed_step(
#     fixed_step_size, coefficient_set=propagation_setup.integrator.CoefficientSets.rk_4
# )

# # Create propagation settings.
# termination_settings = propagation_setup.propagator.time_termination(
#     simulation_end_epoch
# )
propagator_settings_noaero = propagation_setup.propagator.translational(
    central_bodies,
    acceleration_models_noaero,
    bodies_to_propagate,
    system_initial_state,
    simulation_start_epoch,
    integrator_settings,
    termination_settings,
    output_variables=dependent_variables_to_save,
)

propagator_settings_noaero.print_settings.print_initial_and_final_conditions = True


###########################################################################
# PROPAGATE ORBIT #########################################################
###########################################################################

# Create simulation object and propagate dynamics.
dynamics_simulator_noaero = simulator.create_dynamics_simulator(
    bodies, propagator_settings_noaero
)

# Retrieve all data produced by simulation
propagation_results_noaero = dynamics_simulator_noaero.propagation_results

# Extract numerical solution for states and dependent variables
state_history_noaero = propagation_results_noaero.state_history
dependent_variables_noaero = propagation_results_noaero.dependent_variable_history

###########################################################################
# WRITE TO RESULTS FILE ###################################################
###########################################################################
os.makedirs('documents_deliverable', exist_ok=True)
results_path = Path("./documents_deliverable/cartesian_results_AE4868_2026_A1_6541356.txt")

cartesian_noaero = np.vstack(list(state_history_noaero.values()))[sorted_indices]
final_time = time_array[-1]
final_cartesian_state_noaero = cartesian_noaero[-1, :]

try:
    with open(results_path, 'r') as file:
        lines = file.readlines()
except FileNotFoundError:
    lines = []

line_to_replace = 2  # (change between questions)
while len(lines) <= line_to_replace:
    lines.append('\n')

output_line = f"{final_time:.16e} {final_cartesian_state_noaero[0]:.16e} {final_cartesian_state_noaero[1]:.16e} {final_cartesian_state_noaero[2]:.16e} {final_cartesian_state_noaero[3]:.16e} {final_cartesian_state_noaero[4]:.16e} {final_cartesian_state_noaero[5]:.16e}\n"
lines[line_to_replace] = output_line

with open(results_path, 'w') as file:
    file.writelines(lines)

###########################################################################
# PLOT POSITION DIFFERENCE MAGNITUDE: NOMINAL VS NO-AERODYNAMICS ##########
###########################################################################

# Extract the position components (first 3 columns) and calculate the difference
# Difference = Nominal (with drag) - Perturbed (without drag)
position_difference = numerical_cartesian[:, 0:3] - cartesian_noaero[:, 0:3]

# Calculate the magnitude of the position difference vector (Euclidean distance)
position_difference_mag = np.linalg.norm(position_difference, axis=1)

# Generate the plot
fig_diff_mag, ax_diff_mag = plt.subplots(figsize=(10, 6))
ax_diff_mag.plot(time_days, position_difference_mag, color='black', linewidth=2)

ax_diff_mag.set_title('Magnitude of Position Difference\n(Nominal vs. No Aerodynamic Acceleration)', fontsize=14, fontweight='bold')
ax_diff_mag.set_xlabel('Time since $t_0$ [days]', fontsize=12)
ax_diff_mag.set_ylabel('$\|\Delta \mathbf{r}\|$ [m]', fontsize=12)
ax_diff_mag.grid(True, alpha=0.6)

# Use scientific notation for the y-axis
ax_diff_mag.ticklabel_format(style='sci', scilimits=(0,0), axis='y')

# Improve layout
plt.tight_layout()

# Save the figure
diff_mag_output_path = os.path.join(output_dir, "position_difference_magnitude_aero_effect_q3.pdf")
plt.savefig(diff_mag_output_path)
print(f"Position difference magnitude plot saved to: {diff_mag_output_path}")

plt.close()

###########################################################################
# PPROPAGATION WITHOUT SRP ACCEL. #########################################
###########################################################################

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle_nosrp = dict(Ganymede=[propagation_setup.acceleration.spherical_harmonic_gravity(2,2),
                                                  propagation_setup.acceleration.aerodynamic()],
                                        Jupiter=[propagation_setup.acceleration.spherical_harmonic_gravity(4,0)],
                                        Sun=[propagation_setup.acceleration.point_mass_gravity()],
                                            #  propagation_setup.acceleration.radiation_pressure()], # CHECK 
                                        Saturn=[propagation_setup.acceleration.point_mass_gravity()],
                                        Europa=[propagation_setup.acceleration.point_mass_gravity()],
                                        Io=[propagation_setup.acceleration.point_mass_gravity()],
                                        Callisto=[propagation_setup.acceleration.point_mass_gravity()],)

# Create global accelerations dictionary.
acceleration_settings_nosrp = {"JUICE": acceleration_settings_on_vehicle_nosrp}

# Create acceleration models.
acceleration_models_nosrp = propagation_setup.create_acceleration_models(
    bodies, acceleration_settings_nosrp, bodies_to_propagate, central_bodies
)

###########################################################################
# CREATE PROPAGATION SETTINGS #############################################
###########################################################################

# # Define initial state.
# system_initial_state = spice.get_body_cartesian_state_at_epoch(
#     target_body_name="JUICE",
#     observer_body_name="Ganymede",
#     reference_frame_name="ECLIPJ2000",
#     aberration_corrections="NONE",
#     ephemeris_time=simulation_start_epoch,
# )
# Get Ganymede gravitational parameter
# ganymede_grav_param = bodies.get("Ganymede").gravitational_parameter
# print(ganymede_grav_param) # debugging
# Transform initial state to keplerian
# system_initial_state_keplerian = element_conversion.cartesian_to_keplerian(system_initial_state, ganymede_grav_param)

# print(system_initial_state) # debugging

# Define required outputs
dependent_variables_to_save = [
    propagation_setup.dependent_variable.keplerian_state( "JUICE", "Ganymede" ),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.spherical_harmonic_gravity_type , "JUICE", "Ganymede"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Io"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.point_mass_gravity_type , "JUICE", "Sun"),
    # propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.radiation_pressure_type , "JUICE", "Sun"),
    propagation_setup.dependent_variable.single_acceleration( propagation_setup.acceleration.aerodynamic_type , "JUICE", "Ganymede" ),
    propagation_setup.dependent_variable.dynamic_pressure("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.aerodynamic_force_coefficients("JUICE", "Ganymede"), # for doing sanity check on C_D
    propagation_setup.dependent_variable.airspeed("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.density("JUICE", "Ganymede"),
    # propagation_setup.dependent_variable.radiation_pressure_coefficient("JUICE", "Sun"), # sanity check
    propagation_setup.dependent_variable.body_mass("JUICE"), # sanity check
    propagation_setup.dependent_variable.relative_position("JUICE", "Sun"),
    propagation_setup.dependent_variable.tnw_to_inertial_rotation_matrix("JUICE", "Ganymede"),
    propagation_setup.dependent_variable.body_fixed_airspeed_velocity("JUICE", "Ganymede")
]

# # Create numerical integrator settings.
# fixed_step_size = 10.0
# integrator_settings = propagation_setup.integrator.runge_kutta_fixed_step(
#     fixed_step_size, coefficient_set=propagation_setup.integrator.CoefficientSets.rk_4
# )

# # Create propagation settings.
# termination_settings = propagation_setup.propagator.time_termination(
#     simulation_end_epoch
# )
propagator_settings_nosrp = propagation_setup.propagator.translational(
    central_bodies,
    acceleration_models_nosrp,
    bodies_to_propagate,
    system_initial_state,
    simulation_start_epoch,
    integrator_settings,
    termination_settings,
    output_variables=dependent_variables_to_save,
)

propagator_settings_nosrp.print_settings.print_initial_and_final_conditions = True


###########################################################################
# PROPAGATE ORBIT #########################################################
###########################################################################

# Create simulation object and propagate dynamics.
dynamics_simulator_nosrp = simulator.create_dynamics_simulator(
    bodies, propagator_settings_nosrp
)

# Retrieve all data produced by simulation
propagation_results_nosrp = dynamics_simulator_nosrp.propagation_results

# Extract numerical solution for states and dependent variables
state_history_nosrp = propagation_results_nosrp.state_history
dependent_variables_nosrp = propagation_results_nosrp.dependent_variable_history

###########################################################################
# WRITE TO RESULTS FILE ###################################################
###########################################################################
os.makedirs('documents_deliverable', exist_ok=True)
results_path = Path("./documents_deliverable/cartesian_results_AE4868_2026_A1_6541356.txt")

cartesian_nosrp = np.vstack(list(state_history_nosrp.values()))[sorted_indices]
final_time = time_array[-1]
final_cartesian_state_nosrp = cartesian_nosrp[-1, :]

try:
    with open(results_path, 'r') as file:
        lines = file.readlines()
except FileNotFoundError:
    lines = []

line_to_replace = 3  # (change between questions)
while len(lines) <= line_to_replace:
    lines.append('\n')

output_line = f"{final_time:.16e} {final_cartesian_state_nosrp[0]:.16e} {final_cartesian_state_nosrp[1]:.16e} {final_cartesian_state_nosrp[2]:.16e} {final_cartesian_state_nosrp[3]:.16e} {final_cartesian_state_nosrp[4]:.16e} {final_cartesian_state_nosrp[5]:.16e}\n"
lines[line_to_replace] = output_line

with open(results_path, 'w') as file:
    file.writelines(lines)

###########################################################################
# PLOT POSITION DIFFERENCE MAGNITUDE: NOMINAL VS NO-AERODYNAMICS ##########
###########################################################################

# Extract the position components (first 3 columns) and calculate the difference
# Difference = Nominal (with drag) - Perturbed (without drag)
position_difference = numerical_cartesian[:, 0:3] - cartesian_nosrp[:, 0:3]

# Calculate the magnitude of the position difference vector (Euclidean distance)
position_difference_mag = np.linalg.norm(position_difference, axis=1)

# Generate the plot
fig_diff_mag, ax_diff_mag = plt.subplots(figsize=(10, 6))
ax_diff_mag.plot(time_days, position_difference_mag, color='black', linewidth=2)

ax_diff_mag.set_title('Magnitude of Position Difference\n(Nominal vs. No SRP Acceleration)', fontsize=14, fontweight='bold')
ax_diff_mag.set_xlabel('Time since $t_0$ [days]', fontsize=12)
ax_diff_mag.set_ylabel('$\|\Delta \mathbf{r}\|$ [m]', fontsize=12)
ax_diff_mag.grid(True, alpha=0.6)

# Use scientific notation for the y-axis
ax_diff_mag.ticklabel_format(style='sci', scilimits=(0,0), axis='y')

# Improve layout
plt.tight_layout()

# Save the figure
diff_mag_output_path = os.path.join(output_dir, "position_difference_magnitude_srp_effect_q3.pdf")
plt.savefig(diff_mag_output_path)
print(f"Position difference magnitude plot saved to: {diff_mag_output_path}")

plt.close()

