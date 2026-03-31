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
import numpy as np
import matplotlib.pyplot as plt

from integrator_analysis_helper_functions import *

current_directory = os.getcwd()

# Load spice kernels.
spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

# Create the bodies for the numerical simulation
bodies = create_bodies()
# print(bodies)  # debugging

# Define list of step size for integrator to take
step_sizes = [2**i for i in range(3, 10)]
# print(step_sizes) # debugging

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
    acceleration_models = get_unperturbed_accelerations(current_central_body, bodies)

    dependent_variables_to_save = [
        propagation_setup.dependent_variable.relative_position( "JUICE", "Callisto" ),
        propagation_setup.dependent_variable.relative_velocity( "JUICE", "Ganymede" )
    ]


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

        # Compute difference w.r.t. analytical solution to file
        central_body_gravitational_parameter = bodies.get_body(
            current_central_body
        ).gravitational_parameter
        keplerian_solution_difference = get_difference_wrt_kepler_orbit(
            state_history, central_body_gravitational_parameter
        )

        # Write results to files
        file_output_identifier = (
            "Q1_step_size_" + str(step_size) + "_phase_index" + str(current_phase)
        )
        write_propagation_results_and_analytical_difference_to_file(
            dynamics_simulator,
            file_output_identifier,
            bodies.get_body(current_central_body).gravitational_parameter,
        )
# Create figures directory if it doesn't exist
figures_dir = "figures"
if not os.path.exists(figures_dir):
    os.makedirs(figures_dir)

# Configuration matching your script's setup
step_sizes = [2**i for i in range(3, 10)]
phase_names = ["Flyby (Callisto)", "Orbit (GCO500)"]

# Lists to store the maximum errors for Question 1b
max_errors_phase_0 = []
max_errors_phase_1 = []

# --- Plotting 1a: Error vs Time (Combined Figure with Shared Legend) ---
fig, axes = plt.subplots(1, 2, figsize=(12, 8))

for current_phase in range(2):
    ax = axes[current_phase]
    
    for step_size in step_sizes:
        # Construct the file name 
        file_name = f"SimulationOutput/Q1_step_size_{step_size}_phase_index{current_phase}_keplerian_difference.dat"
        
        if os.path.exists(file_name):
            # Load data
            data = np.loadtxt(file_name)
            time = data[:, 0]
            
            # Calculate the magnitude of the position error
            pos_error_mag = np.linalg.norm(data[:, 1:4], axis=1)
            
            # Normalize time to start at 0 and convert to hours
            time_hours = (time - time[0]) / 3600.0
            
            # Plot Error vs Time on the current subplot
            ax.semilogy(time_hours, pos_error_mag, label=f"$\Delta t$ = {step_size} s", linewidth=2)
            
            # Extract and store the maximum error for the 1b plot
            max_error = np.max(pos_error_mag)
            if current_phase == 0:
                max_errors_phase_0.append(max_error)
            else:
                max_errors_phase_1.append(max_error)
        else:
            print(f"Warning: File {file_name} not found. Check the file path and extension.")

    # Format the current phase's subplot
    ax.set_title(f"{phase_names[current_phase]}", fontsize=25, fontweight='bold')
    ax.set_xlabel("Time [hours]", fontsize=22)
    ax.set_ylabel(r"$||\epsilon_r(t; \Delta t)||$ [m]", fontsize=22)
    ax.tick_params(labelsize=20)
    ax.grid(True, which="both", ls="--", alpha=0.5)

# Create a shared legend for both subplots
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=4, frameon=True, fontsize=20)
plt.tight_layout()
plt.subplots_adjust(bottom=0.25)

# Save the combined figure
plt.savefig(f"{figures_dir}/Q1_error_vs_time_combined.pdf", format='pdf', dpi=150, bbox_inches='tight')
plt.close() # Close the figure to free up memory before the next loop iteration

# --- Plotting 1b: Max Error vs Time Step ---
plt.figure(figsize=(8, 8))

if max_errors_phase_0:
    plt.loglog(step_sizes, max_errors_phase_0, marker='o', label=phase_names[0], linewidth=2, markersize=8)
if max_errors_phase_1:
    plt.loglog(step_sizes, max_errors_phase_1, marker='s', label=phase_names[1], linewidth=2, markersize=8)
# Add reference line for order of global truncation error (RKF7(8) has order 7)
# y = C * x^7, use last data point to set the constant
order = 7
if max_errors_phase_0 and max_errors_phase_1:
    # Get current axis limits before plotting
    ax = plt.gca()
    xlim_before = ax.get_xlim()
    ylim_before = ax.get_ylim()
    
    # Use the last phase for reference
    C = max_errors_phase_0[-1] / (step_sizes[-1] ** order)
    
    # Create extended x range for the reference line across the entire plot
    x_extended = np.logspace(np.log10(xlim_before[0]), np.log10(xlim_before[1]), 100)
    reference_line = C * (x_extended ** order)
    
    plt.loglog(x_extended, reference_line, 'k--', linewidth=2, label=f'Order {order} (theoretical)', alpha=0.7)
    
    # Restore original axis limits
    ax.set_xlim(xlim_before)
    ax.set_ylim(ylim_before)
plt.title("Maximum Position Error vs. Time Step", fontsize=20, fontweight='bold')
plt.xlabel(r"Time Step $\Delta t$ [s]", fontsize=22)
plt.ylabel(r"Maximum Position Error $\epsilon_{max}$ [m]", fontsize=22)
plt.tick_params(labelsize=20)
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend(fontsize=20)
plt.tight_layout()
plt.savefig(f"{figures_dir}/Q1_max_error_vs_timestep.pdf", format='pdf', dpi=150)
plt.close()


# --- Additional Plot: Both phases with 3 lowest time steps (same style as big plot) ---
fig, axes = plt.subplots(1, 2, figsize=(12, 8))

# Use only the 3 lowest time steps
lowest_step_sizes = [8, 16, 32]
phase_names_low = ["Flyby (Callisto)", "Orbit (GCO500)"]

for current_phase in range(2):
    ax = axes[current_phase]
    
    for step_size in lowest_step_sizes:
        # Construct the file name 
        file_name = f"SimulationOutput/Q1_step_size_{step_size}_phase_index{current_phase}_keplerian_difference.dat"
        
        if os.path.exists(file_name):
            # Load data
            data = np.loadtxt(file_name)
            time = data[:, 0]
            
            # Calculate the magnitude of the position error
            pos_error_mag = np.linalg.norm(data[:, 1:4], axis=1)
            
            # Normalize time to start at 0 and convert to hours
            time_hours = (time - time[0]) / 3600.0
            
            # Plot Error vs Time on the current subplot
            ax.semilogy(time_hours, pos_error_mag, label=f"$\Delta t$ = {step_size} s", linewidth=2)
        else:
            print(f"Warning: File {file_name} not found.")

    # Format the current phase's subplot
    ax.set_title(f"{phase_names_low[current_phase]}", fontsize=25, fontweight='bold')
    ax.set_xlabel("Time [hours]", fontsize=22)
    ax.set_ylabel(r"$||\epsilon_r(t; \Delta t)||$ [m]", fontsize=22)
    ax.tick_params(labelsize=20)
    ax.grid(True, which="both", ls="--", alpha=0.5)

# Create a shared legend for both subplots
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=True, fontsize=20)
plt.tight_layout()
plt.subplots_adjust(bottom=0.25)

# Save the combined figure
plt.savefig(f"{figures_dir}/Q1_error_vs_time_low_timesteps.pdf", format='pdf', dpi=150, bbox_inches='tight')
plt.close()