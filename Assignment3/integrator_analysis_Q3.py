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
import matplotlib.pyplot as plt

# Set uniform plotting style for all figures
from integrator_analysis_helper_functions import *

# Setup uniform plotting style
setup_uniform_plotting_style()

current_directory = os.getcwd()

prop_count = 0 # debugging

spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

bodies = create_bodies()

# Define list of integrator tolerances
integration_tolerances = [1.0e-12, 1.0e-10, 1.0e-8, 1.0e-6]

benchmark_time_step = [10, 20]

bodies_to_propagate = ["JUICE"]

# Iterate over the mission phases
for current_phase in range(len(central_bodies_per_phase)):

    # Create initial state and time
    current_phase_start_time = initial_times_per_phase[current_phase]
    current_phase_end_time = (
        current_phase_start_time + propagation_times_per_phase[current_phase]
    )

    # Define central body of propagation
    current_central_body = central_bodies_per_phase[current_phase]

    # Define termination conditions (enforce exact termination time)
    termination_condition = propagation_setup.propagator.time_termination(
        current_phase_end_time, terminate_exactly_on_final_condition=True
    )

    # Create acceleration models for perturbed case
    perturbed_acceleration_models = get_perturbed_accelerations(
        current_central_body, bodies
    )

    # Define integrator settings for benchmark
    benchmark_integrator_settings = get_fixed_step_size_integrator_settings(benchmark_time_step[current_phase])


    # Retrieve JUICE initial state
    initial_state = spice.get_body_cartesian_state_at_epoch(
        target_body_name="JUICE",
        observer_body_name=current_central_body,
        reference_frame_name=global_frame_orientation,
        aberration_corrections="NONE",
        ephemeris_time=current_phase_start_time,
    )

    # Create propagator settings for perturbed case
    benchmark_perturbed_propagator_settings = propagation_setup.propagator.translational(
            [current_central_body],
            perturbed_acceleration_models,
            bodies_to_propagate,
            initial_state,
            current_phase_start_time,
            benchmark_integrator_settings,
            termination_condition,
            output_variables=[],
        )

    # Propagate benchmark dynamics
    benchmark_dynamics_simulator = simulator.create_dynamics_simulator(
            bodies, benchmark_perturbed_propagator_settings
        )

    # Create interpolator for benchmark results
    interpolator_settings = interpolators.lagrange_interpolation(8)
    benchmark_interpolator = interpolators.create_one_dimensional_vector_interpolator(
        benchmark_dynamics_simulator.propagation_results.state_history,
        interpolator_settings,
    )

    benchmark_state_history = benchmark_dynamics_simulator.propagation_results.state_history

    # Perform integration of dynamics with different tolerances
    for current_tolerance in integration_tolerances:

        # Define integrator step settings
        initial_time_step = 10.0
        minimum_step_size = 1.0e-12
        maximum_step_size = np.inf

        # Create integrator settings
        step_size_validation_settings = propagation_setup.integrator.step_size_validation(
            minimum_step = minimum_step_size,
            maximum_step = maximum_step_size
        )

        # Retrieve coefficient set
        coefficient_set = propagation_setup.integrator.CoefficientSets.rkf_78 
        # print(coefficient_set) # debugging 

        # Create integrator settings
        # print(current_tolerance) # debugging
        step_size_control_settings = (
            propagation_setup.integrator.step_size_control_elementwise_scalar_tolerance(
                relative_error_tolerance = current_tolerance,
                absolute_error_tolerance = current_tolerance
            )
        )

        block_indices = [(0, 0, 3, 1), (3, 0, 3, 1)]
        step_size_control_settings_blockwise = (
            propagation_setup.integrator.step_size_control_blockwise_scalar_tolerance(
                block_indices, current_tolerance, current_tolerance
            )
        )

        # Create variable step-size integrator settings
        integrator_settings = (
            propagation_setup.integrator.runge_kutta_variable_step(
                initial_time_step = initial_time_step,
                coefficient_set = coefficient_set,
                step_size_control_settings = step_size_control_settings, 
                step_size_validation_settings = step_size_validation_settings
            )
        )

        blockwise_integrator_settings = (
            propagation_setup.integrator.runge_kutta_variable_step(
                initial_time_step = initial_time_step,
                coefficient_set = coefficient_set,
                step_size_control_settings = step_size_control_settings_blockwise, 
                step_size_validation_settings = step_size_validation_settings
            )
        )

        perturbed_propagator_settings = propagation_setup.propagator.translational(
            [current_central_body],
            perturbed_acceleration_models,
            bodies_to_propagate,
            initial_state,
            current_phase_start_time,
            integrator_settings,
            termination_condition,
            output_variables=[],
        )

        blockwise_propagator_settings = propagation_setup.propagator.translational(
            [current_central_body],
            perturbed_acceleration_models,
            bodies_to_propagate,
            initial_state,
            current_phase_start_time,
            blockwise_integrator_settings,
            termination_condition,
            output_variables=[],
        )

        # Define output file name
        file_output_identifier = (
            "Q3_tolerance_index_"
            + str(integration_tolerances.index(current_tolerance))
            + "_phase_index"
            + str(current_phase)
        )

        blockwise_file_output_identifier = (
            "Q3_blockwise_tolerance_index_"
            + str(integration_tolerances.index(current_tolerance))
            + "_phase_index"
            + str(current_phase)
        )

        # Propagate dynamics for perturbed and unperturbed case
        perturbed_dynamics_simulator = simulator.create_dynamics_simulator(
            bodies, perturbed_propagator_settings
        )

        blockwise_dynamics_simulator = simulator.create_dynamics_simulator(
            bodies, blockwise_propagator_settings
        )

        write_propagation_results_and_benchmark_difference_to_file(
            perturbed_dynamics_simulator, file_output_identifier, benchmark_interpolator
        )

        write_propagation_results_and_benchmark_difference_to_file(
            blockwise_dynamics_simulator, blockwise_file_output_identifier, benchmark_interpolator
        )

        prop_count += 1 # debugging
        # print('propagation number', prop_count) # debugging


figures_dir = "figures"
if not os.path.exists(figures_dir):
    os.makedirs(figures_dir)

phase_names = ["Flyby (Callisto)", "Orbit (GCO500)"]

# =====================================================================
# Plotting 3a: Error vs Time for different tolerances
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    
    points_to_trim = 5 if phase_idx == 1 else 0  # Only trim for orbit, not flyby
    
    for tol_idx, tolerance in enumerate(integration_tolerances):
        file_name = f"SimulationOutput/Q3_tolerance_index_{tol_idx}_phase_index{phase_idx}_benchmark_difference.dat"
        
        if os.path.exists(file_name):
            data = np.loadtxt(file_name)
            time = data[:, 0]
            time_hours = (time - time[0]) / 3600.0
            
            if points_to_trim > 0:
                time_hours_trimmed = time_hours[points_to_trim:-points_to_trim]
            else:
                time_hours_trimmed = time_hours
            
            # Cartesian position error magnitude
            pos_error_mag = np.linalg.norm(data[:, 1:4], axis=1)
            if points_to_trim > 0:
                pos_error_mag_trimmed = pos_error_mag[points_to_trim:-points_to_trim]
            else:
                pos_error_mag_trimmed = pos_error_mag
            
            plt.semilogy(time_hours_trimmed, pos_error_mag_trimmed, label=f"Tol = {tolerance}")
        else:
            print(f"Warning: {file_name} not found.")


    plt.xlabel("Time [hours]")
    plt.ylabel(r"$||\epsilon_r(t)|| \approx ||r(t) - \bar{r}(t)||$ [m]")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    save_figure(f"Q3a_error_vs_time_{phase_label}.pdf")
    plt.close()

# =====================================================================
# Plotting 3b: Time Step Size vs Time for different tolerances
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    
    for tol_idx, tolerance in enumerate(integration_tolerances):
        file_name = f"SimulationOutput/Q3_tolerance_index_{tol_idx}_phase_index{phase_idx}_benchmark_difference.dat"
        
        if os.path.exists(file_name):
            data = np.loadtxt(file_name)
            time = data[:, 0]
            time_hours = (time - time[0]) / 3600.0
            
            # Compute time steps (dt = t_{i+1} - t_i)
            # The time array represents epochs, so np.diff gives the step taken to reach the next epoch
            dt_array = np.diff(time)
            time_plot = time_hours[1:]  # Plot timestep at the endpoint of the interval
            
            plt.semilogy(time_plot, dt_array, label=f"Tol = {tolerance}", alpha=0.8)


    plt.xlabel("Time [hours]")
    plt.ylabel(r"Time Step $\Delta t$ [s]")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    # Restrict the x-axis for GCO500 to show a single orbit (185 minutes) 
    # Source https://spiftp.esac.esa.int/data/ANCDR/JUICE/man/JUICE_CReMA_Issue_4_Revision_2/Memo_20200429_JUICE_GCO_Cycles.pdf
    initial_plot_time_limit = 3
    GCO500_period_hours = 185 / 60
    if phase_idx == 1:
        plt.xlim(initial_plot_time_limit, initial_plot_time_limit + GCO500_period_hours) 
        
    plt.tight_layout()
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    save_figure(f"Q3b_timestep_vs_time_{phase_label}.pdf")
    plt.close()


# =====================================================================
# Plotting 3c: Error vs Time for blockwise tolerances
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    
    points_to_trim = 5 if phase_idx == 1 else 0  # Only trim for orbit, not flyby
    
    for tol_idx, tolerance in enumerate(integration_tolerances):
        # Fetch the blockwise files specifically
        file_name = f"SimulationOutput/Q3_blockwise_tolerance_index_{tol_idx}_phase_index{phase_idx}_benchmark_difference.dat"
        
        if os.path.exists(file_name):
            data = np.loadtxt(file_name)
            time = data[:, 0]
            time_hours = (time - time[0]) / 3600.0
            
            if points_to_trim > 0:
                time_hours_trimmed = time_hours[points_to_trim:-points_to_trim]
            else:
                time_hours_trimmed = time_hours
            
            # Cartesian position error magnitude
            pos_error_mag = np.linalg.norm(data[:, 1:4], axis=1)
            if points_to_trim > 0:
                pos_error_mag_trimmed = pos_error_mag[points_to_trim:-points_to_trim]
            else:
                pos_error_mag_trimmed = pos_error_mag
            
            plt.semilogy(time_hours_trimmed, pos_error_mag_trimmed, label=f"Tol = {tolerance}")
        else:
            print(f"Warning: {file_name} not found.")

    plt.xlabel("Time [hours]")
    plt.ylabel(r"||\\epsilon_r(t)|| \\approx ||r(t) - \\bar{r}(t)||$ [m]")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    save_figure(f"Q3c_blockwise_error_vs_time_{phase_label}.pdf")
    plt.close()

# =====================================================================
# Plotting 3d: Time Step Size vs Time for blockwise tolerances
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    
    for tol_idx, tolerance in enumerate(integration_tolerances):
        file_name = f"SimulationOutput/Q3_blockwise_tolerance_index_{tol_idx}_phase_index{phase_idx}_benchmark_difference.dat"
        
        if os.path.exists(file_name):
            data = np.loadtxt(file_name)
            time = data[:, 0]
            time_hours = (time - time[0]) / 3600.0
            
            # Compute time steps (dt = t_{i+1} - t_i)
            dt_array = np.diff(time)
            time_plot = time_hours[1:]  # Plot timestep at the endpoint of the interval
            
            plt.semilogy(time_plot, dt_array, label=f"Tol = {tolerance}", alpha=0.8)


    plt.xlabel("Time [hours]")
    plt.ylabel(r"Time Step $\Delta t$ [s]")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    initial_plot_time_limit = 3
    GCO500_period_hours = 185 / 60
    if phase_idx == 1:
        plt.xlim(initial_plot_time_limit, initial_plot_time_limit + GCO500_period_hours) 
        
    plt.tight_layout()
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    save_figure(f"Q3d_blockwise_timestep_vs_time_{phase_label}.pdf")
    plt.close()