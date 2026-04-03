"""
Copyright (c) 2010-2020, Delft University of Technology
All rigths reserved

This file is part of the Tudat. Redistribution and use in source and
binary forms, with or without modification, are permitted exclusively
under the terms of the Modified BSD license. You should have received
a copy of the license with this file. If not, please or visit:
http://tudat.tudelft.nl/LICENSE.
"""

import os

from integrator_analysis_helper_functions import *

current_directory = os.getcwd()

spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

bodies = create_bodies()

# Define settings for orbit only, unperturbed only
current_phase = 1
central_body = "Ganymede"
bodies_to_integrate = ["JUICE"]
central_bodies = [central_body]
current_phase_start_time = initial_times_per_phase[current_phase]
acceleration_models = get_unperturbed_accelerations(central_body, bodies)

n_prop = 20

state_differences_rkf = np.zeros((6, n_prop))
state_differences_euler = np.zeros((6, n_prop))

step_per_run = 600.0

# local_truncation_error_rk = np.zeros(n_prop)
# local_truncation_error_euler = np.zeros(n_prop)

# Perform 20 individual steps
for i in range(n_prop):

    # Compute initial time of current step
    current_start_time = initial_times_per_phase[current_phase] + i * step_per_run
    # Define central body of propagation
    current_central_body = central_bodies_per_phase[current_phase]


    # Compute initial state of current step
    initial_state = spice.get_body_cartesian_state_at_epoch(
        target_body_name="JUICE",
        observer_body_name=current_central_body,
        reference_frame_name=global_frame_orientation,
        aberration_corrections="NONE",
        ephemeris_time=current_start_time,
    )

    """
    RKF
    """

    # Get fixed step RKF78 integrator settings
    time_step = 300.0
    integrator_settings = get_fixed_step_size_integrator_settings(time_step)

    # Define propagator settings, terminate after 300 s.
    termination_time = current_start_time + time_step
    termination_settings = propagation_setup.propagator.time_termination(
        termination_time, terminate_exactly_on_final_condition=True
    )
    propagator_settings = propagation_setup.propagator.translational(
            [current_central_body],
            acceleration_models,
            bodies_to_integrate,
            initial_state,
            current_start_time,
            integrator_settings,
            termination_settings,
            output_variables=[],
        )

    # Propagate Dynamics
    dynamics_simulator = simulator.create_dynamics_simulator(
            bodies, propagator_settings
        )
    
    state_history = dynamics_simulator.propagation_results.state_history

    # Compute difference w.r.t. analytical solution to file
    central_body_gravitational_parameter = bodies.get_body(
        current_central_body
    ).gravitational_parameter
    keplerian_solution_difference = get_difference_wrt_kepler_orbit(
        state_history, central_body_gravitational_parameter
    )

    final_state_difference = list(keplerian_solution_difference.values())[-1]
    # local_truncation_error_rk[i] = np.linalg.norm(keplerian_solution_difference[:3])

    state_differences_rkf[:, i] = final_state_difference

    """
    Euler
    """

    # Get fixed step euler integrator settings
    time_step_euler = 10.0

    coefficient_set_euler = propagation_setup.integrator.euler_forward 
    integrator_settings_euler = propagation_setup.integrator.runge_kutta_fixed_step_size(
        time_step_euler, coefficient_set_euler
    )

    # Define propagator settings, terminate after 10 s.
    termination_time_euler = current_start_time + time_step_euler
    termination_settings_euler = propagation_setup.propagator.time_termination(
        termination_time_euler, terminate_exactly_on_final_condition=True
    )
    propagator_settings_euler = propagation_setup.propagator.translational(
            [current_central_body],
            acceleration_models,
            bodies_to_integrate,
            initial_state,
            current_start_time,
            integrator_settings_euler,
            termination_settings_euler,
            output_variables=[],
        )

    # Propagate Dynamics
    dynamics_simulator_euler = simulator.create_dynamics_simulator(
            bodies, propagator_settings_euler
        )
    
    state_history_euler = dynamics_simulator_euler.propagation_results.state_history

    # Compute difference w.r.t. analytical solution to file
    keplerian_solution_difference_euler = get_difference_wrt_kepler_orbit(
        state_history_euler, central_body_gravitational_parameter
    )

    final_state_difference_euler = list(keplerian_solution_difference_euler.values())[-1]

    state_differences_euler[:, i] = final_state_difference_euler

local_truncation_error_rk = np.linalg.norm(state_differences_rkf[:3, :], axis=0)
local_truncation_error_euler = np.linalg.norm(state_differences_euler[:3, :], axis=0)

K_r_rk = local_truncation_error_rk / (time_step ** 9) # rk8 is 8th order, p+1=9
K_r_euler = local_truncation_error_euler / (time_step_euler ** 2) # euler is 1st order, p+1=2

# print(state_differences_euler.shape) # debugging
# print(state_history) # debugging
# print(keplerian_solution_difference) # debugging

figures_dir = "figures"
if not os.path.exists(figures_dir):
    os.makedirs(figures_dir)

# Normalize time array to hours for plotting (20 steps, separated by 600 seconds)
# t = 0 represents the start of the GCO500 orbit phase
times_seconds = np.array([i * 600.0 for i in range(n_prop)])
times_hours = times_seconds / 3600.0

# =====================================================================
# PLACEHOLDERS: You must compute these mathematically for Q5(b) and 5(c)
# =====================================================================
# theoretical_K_r_rk = ...   # Your derived analytical K_r for RKF7(8)
# theoretical_K_r_euler = ... # Your derived analytical K_r for Euler

# (Dummy arrays used here just so the plotting script runs without crashing)
theoretical_K_r_rk = np.zeros(n_prop) 
theoretical_K_r_euler = np.zeros(n_prop) 

# =====================================================================
# Plotting 5a & 5b: Error Constant Kr(t) for RKF7(8)
# =====================================================================
plt.figure(figsize=(10, 6))

plt.semilogy(times_hours, K_r_rk, marker='o', linestyle='-', color='blue', label='Numerical $||K_r(t)||$')
plt.semilogy(times_hours, theoretical_K_r_rk, marker='s', linestyle='--', color='orange', label='Theoretical $||K_r(t)||$')

plt.title("Local Truncation Error Constant $K_r(t)$: RKF7(8)")
plt.xlabel("Time since start of phase [hours]")
plt.ylabel(r"Error Constant $||K_r(t)||$")
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(f"{figures_dir}/Q5_Kr_RKF78.pdf", format='pdf', dpi=150)
plt.close()

# =====================================================================
# Plotting 5c: Error Constant Kr(t) for Euler
# =====================================================================
plt.figure(figsize=(10, 6))

plt.semilogy(times_hours, K_r_euler, marker='o', linestyle='-', color='green', label='Numerical $||K_r(t)||$')
plt.semilogy(times_hours, theoretical_K_r_euler, marker='s', linestyle='--', color='purple', label='Theoretical $||K_r(t)||$')

plt.title("Local Truncation Error Constant $K_r(t)$: Euler")
plt.xlabel("Time since start of phase [hours]")
plt.ylabel(r"Error Constant $||K_r(t)||$")
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(f"{figures_dir}/Q5_Kr_Euler.pdf", format='pdf', dpi=150)
plt.close()