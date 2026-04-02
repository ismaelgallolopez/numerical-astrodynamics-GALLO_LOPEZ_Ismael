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

# Load spice kernels.
spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

# Create the bodies for the numerical simulation
bodies = create_bodies()

# Define list of step size for integrator to take
step_sizes = [2**i for i in range(2, 10)]
# print(step_sizes) # debugging
benchmark_time_step = [10, 20]

errors_comparison = {}

# Iterate over phases
for current_phase in range(len(central_bodies_per_phase)):

    # Create initial state and time
    current_phase_start_time = initial_times_per_phase[current_phase]
    current_phase_end_time = (
        current_phase_start_time + propagation_times_per_phase[current_phase]
    )

    termination_settings = propagation_setup.propagator.time_termination(
        current_phase_end_time
    )

    # Define current centra
    current_central_body = central_bodies_per_phase[current_phase]
    # if current_central_body == "Ganymede":
    #     step_sizes[0] = 2*step_sizes[0]
    
    # print(step_sizes) # debugging

    # Retrieve JUICE initial state
    initial_state = spice.get_body_cartesian_state_at_epoch(
        target_body_name="JUICE",
        observer_body_name=current_central_body,
        reference_frame_name=global_frame_orientation,
        aberration_corrections="NONE",
        ephemeris_time=current_phase_start_time,
    )

    bodies_to_propagate = ["JUICE"]

    # Retrieve acceleration settings without perturbations
    acceleration_models = get_perturbed_accelerations(current_central_body, bodies)

    # Save propagation results for each time step into a list, for analysis after all propagations are done
    propagation_results_per_step_size = list()

    dependent_variables_to_save = [
        propagation_setup.dependent_variable.relative_position( "JUICE", "Callisto" ),
        propagation_setup.dependent_variable.relative_velocity( "JUICE", "Ganymede" )
    ]


    # setup of the benchmark propagation
    benchmark_integrator_settings = get_fixed_step_size_integrator_settings(benchmark_time_step[current_phase])
    # print(benchmark_time_step[current_phase]) # debugging
    benchmark_propagator_settings = propagation_setup.propagator.translational(
            [current_central_body],
            acceleration_models,
            bodies_to_propagate,
            initial_state,
            current_phase_start_time,
            benchmark_integrator_settings,
            termination_settings,
            output_variables=dependent_variables_to_save,
        )
    dynamics_simulator = simulator.create_dynamics_simulator(
            bodies, benchmark_propagator_settings
        )
    benchmark_state_history = dynamics_simulator.propagation_results.state_history
    # print(benchmark_state_history) # debugging
    
    interpolator_settings = interpolators.lagrange_interpolation(8) # 8th order lagrange interpolation, as requested
    
    benchmark_interpolator = interpolators.create_one_dimensional_vector_interpolator(
        benchmark_state_history, 
        interpolator_settings
    )
    
    min_epoch = min(benchmark_state_history.keys())
    max_epoch = max(benchmark_state_history.keys())
    time_limits = (min_epoch, max_epoch)

    # Iterate over step size
    for step_size in step_sizes:

        # Define integrator settings
        integrator_settings = get_fixed_step_size_integrator_settings(step_size)

        # Define propagator settings
        propagator_settings = propagation_setup.propagator.translational(
            [current_central_body],
            acceleration_models,
            bodies_to_propagate,
            initial_state,
            current_phase_start_time,
            integrator_settings,
            termination_settings,
            output_variables=dependent_variables_to_save,
        )

        # Propagate dynamics
        dynamics_simulator = simulator.create_dynamics_simulator(
            bodies, propagator_settings
        )
        state_history = dynamics_simulator.propagation_results.state_history
        propagation_results_per_step_size.append(state_history)

        # Write results to files
        file_output_identifier = (
            "Q2_step_size_" + str(step_size) + "_phase_index" + str(current_phase)
        )
        write_propagation_results_and_benchmark_difference_to_file(
            dynamics_simulator,
            file_output_identifier,
            benchmark_interpolator,
            time_limits,
        )

    for i, step_size in enumerate(step_sizes[1:]): 
        dt_coarse = step_size
        dt_fine = step_sizes[i]
        # print(dt_coarse, dt_fine) # debugging
        
        times, errors = compare_different_timesteps(dt_coarse, dt_fine, current_phase)
        
        key = f"Phase {current_phase} (dt={dt_coarse} vs {dt_fine})"
        errors_comparison[key] = {
            'phase': current_phase,
            'dt_coarse': dt_coarse,
            'dt_fine': dt_fine,
            'times': times,
            'errors': errors,
        }


figures_dir = "figures"
if not os.path.exists(figures_dir):
    os.makedirs(figures_dir)

phase_names = ["Flyby (Callisto)", "Orbit (GCO500)"]
# Use your standard step sizes (ignoring the 4s step used only for calculating the 8s error)
standard_step_sizes = [2**i for i in range(3, 10)]

# =====================================================================
# Plotting 2a: Error vs Time (Delta t / 2 Method) from Dictionary
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    
    for step_size in standard_step_sizes:
        # Reconstruct the exact dictionary key you created in your loop
        # Note: dt_fine is the smaller step (step_size / 2)
        key = f"Phase {phase_idx} (dt={step_size} vs {int(step_size/2)})"
        
        if key in errors_comparison:
            data = errors_comparison[key]
            
            points_to_trim = 0
            if len(data['times']) > 2 * points_to_trim:
                times_trimmed = data['times'][points_to_trim:-points_to_trim]
                errors_trimmed = data['errors'][points_to_trim:-points_to_trim]
            else:
                times_trimmed = data['times']
                errors_trimmed = data['errors']
            
            # Normalize time to hours
            time_hours = (np.array(times_trimmed) - data['times'][0]) / 3600.0
            
            plt.semilogy(time_hours, errors_trimmed, label=f"$\Delta t$ = {step_size} s")
        else:
            print(f"Warning: Dictionary key '{key}' not found for 2a plotting.")
            
    plt.title(f"Integration Error ($\Delta t/2$ Method): {phase_names[phase_idx]}")
    plt.xlabel("Time [hours]")
    plt.ylabel(r"$||\epsilon_r(t; \Delta t)|| \approx ||r(\Delta t) - r(\Delta t/2)||$ [m]")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    plt.savefig(f"{figures_dir}/Q2a_error_vs_time_{phase_label}.pdf", format='pdf', dpi=150)
    plt.close()


# =====================================================================
# Plotting 2b: Error vs Time (Benchmark Method) from Files
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    
    for step_size in standard_step_sizes:
        # Verify this suffix matches exactly what your helper function outputs!
        file_name = f"SimulationOutput/Q2_step_size_{step_size}_phase_index{phase_idx}_benchmark_difference.dat"
        
        if os.path.exists(file_name):
            data = np.loadtxt(file_name)
            time = data[:, 0]
            
            points_to_trim = 10
            if len(time) > 2 * points_to_trim:
                time_trimmed = time[points_to_trim:-points_to_trim]
                error_data_trimmed = data[points_to_trim:-points_to_trim, 1:4]
            else:
                time_trimmed = time
                error_data_trimmed = data[:, 1:4]
            
            # Calculate Cartesian magnitude
            pos_error_mag = np.linalg.norm(error_data_trimmed, axis=1)
            time_hours = (time_trimmed - data[0, 0]) / 3600.0
            
            plt.semilogy(time_hours, pos_error_mag, label=f"$\Delta t$ = {step_size} s")
        else:
            print(f"Warning: File {file_name} not found for 2b plotting.")
            
    plt.title(f"Integration Error (Benchmark Method): {phase_names[phase_idx]}")
    plt.xlabel("Time [hours]")
    plt.ylabel(r"$||\epsilon_r(t; \Delta t)|| \approx ||r(\Delta t) - \bar{r}(t)||$ [m]")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    plt.savefig(f"{figures_dir}/Q2b_error_vs_time_{phase_label}.pdf", format='pdf', dpi=150)
    plt.close()