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
simulation_end_epoch = simulation_start_epoch + 1e-1 * constants.JULIAN_DAY / 24.0 # debugging 
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
central_bodies = ["Ganymede"]

# Define accelerations acting on vehicle.
acceleration_settings_on_vehicle = dict(
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
acceleration_settings = {"JUICE": acceleration_settings_on_vehicle}

# Create acceleration models.
acceleration_models = propagation_setup.create_acceleration_models(
    bodies, 
    acceleration_settings, 
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

# Extract numerical solution for states and dependent 
state_history = propagation_results.state_history
state_array = result2array(state_history)
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

###########################################################################
# VALIDATING ACCELERATIONS ################################################
###########################################################################

c = constants.SPEED_OF_LIGHT # m/s
P = 3.828e26 # W https://en.wikipedia.org/wiki/Solar_luminosity

# extraction of dependent variables 
dep_vars = propagation_results.dependent_variable_history
dep_vars_array = result2array(dep_vars)
# print(dep_vars_array[0]) # debugging
dep_var_dict = create_dependent_variable_dictionary(dynamics_simulator)

dep_vars_matrix = np.vstack(list(dependent_variables.values()))[sorted_indices]
dep_vars_ids = propagation_results.dependent_variable_ids

print("Dependent variable IDs: ", dep_vars_ids) # debugging

if not len(dep_vars_array[0]) == 45: # debugging in case that more dependent variables are added
    raise ValueError(f"Expected 44 dependent variables, but got {len(dep_vars_array[0])-1}") # debugging in case that more dependent variables are added

# print(dep_vars_matrix) # debugging

# Remember to add 1 to the IDs because of result2array implementation
mass_sanity_check = dep_vars_array[:,29]
print(f"Mass sanity check: {mass_sanity_check[0]} kg") # debugging
# aerodynamic_coeffs = dep_vars_matrix[:, 22:25] # only for sanity check of drag
# print(aerodynamic_coeffs[0]) # print first aerodynamic coefficient

# dynamic_pressure_old = dep_vars_array[:, 22]
dynamic_pressure = dep_var_dict.asarray(propagation_setup.dependent_variable.dynamic_pressure("JUICE", "Ganymede"))
# print(dynamic_pressure - dynamic_pressure_old) # debugging
density = dep_var_dict.asarray(propagation_setup.dependent_variable.density("JUICE", "Ganymede"))
sun_juice_position = dep_var_dict.asarray(propagation_setup.dependent_variable.relative_position("JUICE", "Sun"))
airspeed = dep_var_dict.asarray(propagation_setup.dependent_variable.airspeed("JUICE", "Ganymede"))
airspeed_vector = dep_var_dict.asarray(propagation_setup.dependent_variable.body_fixed_airspeed_velocity("JUICE", "Ganymede"))
radiation_pressure_coeff_sanity = dep_var_dict.asarray(propagation_setup.dependent_variable.radiation_pressure_coefficient("JUICE", "Sun"))


# sanity checks
if not np.allclose(dynamic_pressure, 0.5 * density * airspeed**2):
    raise ValueError(f"Dynamic pressure does not match. Residual =  {dynamic_pressure - 0.5 * density * airspeed**2}") # sanity check
if not np.allclose(radiation_pressure_coeff_sanity, rad_pres_coeff_juice):
    raise ValueError(f"Radiation pressure coefficient does not match. Expected: {rad_pres_coeff_juice}, Got: {radiation_pressure_coeff_sanity[0]}") # sanity check

# calculation of accelerations for validation

#aerodynamic acceleration
airspeed_vector_inertial = np.zeros_like(airspeed_vector)
for i, epoch in enumerate(time_array):
    rot_matrix = spice.compute_rotation_matrix_between_frames(
        "IAU_GANYMEDE", "ECLIPJ2000", epoch
    )
    airspeed_vector_inertial[i, :] = rot_matrix @ airspeed_vector[i, :]

airspeed_norm = np.linalg.norm(airspeed_vector_inertial, axis=1)[:, np.newaxis]
airspeed_unitary_vector_inertial = airspeed_vector_inertial / airspeed_norm


accel_aerodynamic_manual_mag = dynamic_pressure * ref_area_juice * drag_coeff_juice / mass_juice
# airspeed_norm = np.linalg.norm(airspeed_vector, axis=1)[:, np.newaxis]
# airspeed_unitary_vector = airspeed_vector / airspeed_norm
accel_aerodynamic_manual = -accel_aerodynamic_manual_mag[:, np.newaxis] * airspeed_unitary_vector_inertial

sun_juice_position_mag = np.linalg.norm(sun_juice_position, axis=1)
# print(sun_juice_position_mag.shape) # debugging
accel_radiation_pressure_manual = (P / (4 * np.pi * c)) * (rad_pres_coeff_juice * ref_area_juice / mass_juice) * sun_juice_position / sun_juice_position_mag[:, np.newaxis]**3
# print(accel_radiation_pressure_manual.shape) # debugging
accel_radiation_pressure_manual_mag = np.linalg.norm(accel_radiation_pressure_manual, axis=1)
# print(accel_radiation_pressure_manual_mag) # debugging

# retrieving of accelerations from simulations
accel_aerodynamic_simulation = dep_vars_array[:, 19:22]
accel_aerodynamic_simulation_mag = np.linalg.norm(accel_aerodynamic_simulation, axis=1)
# print(accel_aerodynamic_simulation_mag) # debugging

accel_radiation_pressure_simulation = dep_vars_array[:, 16:19]
accel_radiation_pressure_simulation_mag = np.linalg.norm(accel_radiation_pressure_simulation, axis=1)
# print(accel_radiation_pressure_simulation_mag) # debugging

###########################################################################
# PLOT ACCELERATION VALIDATION (DIFFERENCES) ##############################
###########################################################################

# Correct the manual aerodynamic magnitude to be strictly positive for comparison
accel_aero_manual_mag_abs = np.abs(accel_aerodynamic_manual_mag)

# Calculate differences (Simulation - Analytical)
diff_aero_mag = accel_aerodynamic_simulation_mag - accel_aero_manual_mag_abs
diff_srp_mag = accel_radiation_pressure_simulation_mag - accel_radiation_pressure_manual_mag
diff_srp_vec = accel_radiation_pressure_simulation - accel_radiation_pressure_manual
diff_aero_vec = accel_aerodynamic_simulation - accel_aerodynamic_manual

# -------------------------------------------------------------------------
# 1. Aerodynamic Magnitude Difference
# -------------------------------------------------------------------------
fig_aero, ax_aero = plt.subplots(figsize=(10, 6))
ax_aero.plot(time_days, diff_aero_mag, color='tab:blue', linewidth=2)

ax_aero.set_title('Aerodynamic Acceleration Magnitude Difference\n(Simulation - Analytical)', fontsize=14, fontweight='bold')
ax_aero.set_xlabel('Time since $t_0$ [days]', fontsize=12)
ax_aero.set_ylabel(r'$\Delta$ Magnitude [$\mathrm{m/s}^2$]', fontsize=12)
ax_aero.grid(True, alpha=0.6)
ax_aero.ticklabel_format(style='sci', scilimits=(0,0), axis='y')

plt.tight_layout()
aero_val_path = os.path.join(output_dir, "validation_aero_mag_diff_q3.pdf")
plt.savefig(aero_val_path)
print(f"Aerodynamic magnitude difference plot saved to: {aero_val_path}")
plt.close()

# -------------------------------------------------------------------------
# 2. Radiation Pressure Magnitude Difference
# -------------------------------------------------------------------------
fig_srp_mag, ax_srp_mag = plt.subplots(figsize=(10, 6))
ax_srp_mag.plot(time_days, diff_srp_mag, color='tab:orange', linewidth=2)

ax_srp_mag.set_title('Solar Radiation Pressure Magnitude Difference\n(Simulation - Analytical)', fontsize=14, fontweight='bold')
ax_srp_mag.set_xlabel('Time since $t_0$ [days]', fontsize=12)
ax_srp_mag.set_ylabel(r'$\Delta$ Magnitude [$\mathrm{m/s}^2$]', fontsize=12)
ax_srp_mag.grid(True, alpha=0.6)
ax_srp_mag.ticklabel_format(style='sci', scilimits=(0,0), axis='y')

plt.tight_layout()
srp_mag_val_path = os.path.join(output_dir, "validation_srp_mag_diff_q3.pdf")
plt.savefig(srp_mag_val_path)
print(f"SRP magnitude difference plot saved to: {srp_mag_val_path}")
plt.close()

# -------------------------------------------------------------------------
# 3. Radiation Pressure Vector Difference
# -------------------------------------------------------------------------
fig_srp_vec, axs_srp_vec = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
fig_srp_vec.suptitle('Solar Radiation Pressure Vector Difference\n(Simulation - Analytical)', fontsize=16, fontweight='bold', y=0.96)

components = ['X', 'Y', 'Z']
colors = ['tab:red', 'tab:green', 'tab:purple']

for i in range(3):
    axs_srp_vec[i].plot(time_days, diff_srp_vec[:, i], color=colors[i], linewidth=2)
    axs_srp_vec[i].set_ylabel(f'$\Delta$ {components[i]} Component [m s^-2]', fontsize=12)
    axs_srp_vec[i].grid(True, alpha=0.6)
    axs_srp_vec[i].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

axs_srp_vec[-1].set_xlabel('Time since $t_0$ [days]', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
srp_vec_val_path = os.path.join(output_dir, "validation_srp_vector_diff_q3.pdf")
plt.savefig(srp_vec_val_path)
print(f"SRP vector difference plot saved to: {srp_vec_val_path}")
plt.close()

# -------------------------------------------------------------------------
# 4. Aerodynamic Acceleration Vector Difference
# -------------------------------------------------------------------------
fig_aero_vec, axs_aero_vec = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
fig_aero_vec.suptitle('Aerodynamic Acceleration Vector Difference\n(Simulation - Analytical)', fontsize=16, fontweight='bold', y=0.96)

components = ['X', 'Y', 'Z']
colors = ['tab:red', 'tab:green', 'tab:purple']

for i in range(3):
    axs_aero_vec[i].plot(time_days, diff_aero_vec[:, i], color=colors[i], linewidth=2)
    axs_aero_vec[i].set_ylabel(f'$\Delta$ {components[i]} Component [m s^-2]', fontsize=12)
    axs_aero_vec[i].grid(True, alpha=0.6)
    axs_aero_vec[i].ticklabel_format(style='sci', scilimits=(0,0), axis='y')

axs_aero_vec[-1].set_xlabel('Time since $t_0$ [days]', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
aero_vec_val_path = os.path.join(output_dir, "validation_aero_vector_diff_q3.pdf")
plt.savefig(aero_vec_val_path)
print(f"Aerodynamic vector difference plot saved to: {aero_vec_val_path}")
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

