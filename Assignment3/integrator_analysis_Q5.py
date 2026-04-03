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

state_differences_rkf = np.zeros((6, 20))
state_differences_euler = np.zeros((6, 20))

step_per_run = 600.0
time_step = 300.0

# Perform 20 individual steps
for i in range(20):

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


    local_truncation_error = ...

    """
    Euler
    """

# print(state_history) # debugging
# print(keplerian_solution_difference) # debugging