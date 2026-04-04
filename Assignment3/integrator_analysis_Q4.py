import glob
import os

from integrator_analysis_helper_functions import *
current_directory = os.getcwd()


for f in glob.glob(os.path.join(current_directory, "SimulationOutput", "Q4*")):
    os.remove(f)

current_directory = os.getcwd()

prop_count = 0 # debugging

spice.load_standard_kernels()
spice.load_kernel(current_directory + "/juice_mat_crema_5_1_150lb_v01.bsp")

bodies = create_bodies()

# Define list of integrator tolerances
integration_tolerances = [1.0e-14, 1.0e-12, 1.0e-10, 1.0e-8, 1.0e-6]
coefficient_set_options = [
    propagation_setup.integrator.CoefficientSets.rkf_45,
    propagation_setup.integrator.CoefficientSets.rkf_56,
    propagation_setup.integrator.CoefficientSets.rkf_78,
]

benchmark_time_step = [10, 20]
step_sizes = [2**i for i in range(3, 10)]

bodies_to_propagate = ["JUICE"]

func_evals_dict = {}

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

    # Define integrator step settings
    initial_time_step = 10.0
    minimum_step_size = 1.0e-12
    maximum_step_size = np.inf

        # Create integrator settings
        # Create integrator settings
    step_size_validation_settings = propagation_setup.integrator.step_size_validation(
            minimum_step = minimum_step_size,
            maximum_step = maximum_step_size
        )

    for current_tolerance in integration_tolerances:
        for coefficient_set in coefficient_set_options:
            # Create step size control settings
            step_size_control_settings = (
                propagation_setup.integrator.step_size_control_elementwise_scalar_tolerance(
                    relative_error_tolerance = current_tolerance,
                    absolute_error_tolerance = current_tolerance
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

            # Define output file name
            file_output_identifier = (
                "Q4_variable_tolerance_index_"
                + str(integration_tolerances.index(current_tolerance))
                + "_coeff_"
                + str(coefficient_set_options.index(coefficient_set))
                + "_phase_"
                + str(current_phase)
            )

            perturbed_dynamics_simulator = simulator.create_dynamics_simulator(
                bodies, perturbed_propagator_settings
            )
            
            func_evals = perturbed_dynamics_simulator.cumulative_number_of_function_evaluations
            func_evals_dict[file_output_identifier] = max(func_evals.values())

            write_propagation_results_and_benchmark_difference_to_file(
                perturbed_dynamics_simulator, file_output_identifier, benchmark_interpolator
            )

            prop_count += 1

    for coefficient_set in coefficient_set_options:
        order_to_use = propagation_setup.integrator.OrderToIntegrate.higher
        if coefficient_set == propagation_setup.integrator.CoefficientSets.rkf_45:
            order_to_use = propagation_setup.integrator.OrderToIntegrate.lower

        for step_size in step_sizes:
            # Create fixed step-size integrator settings
            integrator_settings = propagation_setup.integrator.runge_kutta_fixed_step_size(
                step_size, coefficient_set, order_to_use
            )
            # Define propagator settings
            propagator_settings = propagation_setup.propagator.translational(
                [current_central_body],
                perturbed_acceleration_models,
                bodies_to_propagate,
                initial_state,
                current_phase_start_time,
                integrator_settings,
                termination_condition,
                output_variables=[],
            )

            # Define output file name
            file_output_identifier = (
                "Q4_fixed_step_size_"
                + str(step_size)
                + "_coeff_"
                + str(coefficient_set_options.index(coefficient_set))
                + "_phase_"
                + str(current_phase)
            )

            # Propagate dynamics and save results
            perturbed_dynamics_simulator = simulator.create_dynamics_simulator(
                bodies, propagator_settings
            )
            
            func_evals = perturbed_dynamics_simulator.cumulative_number_of_function_evaluations
            func_evals_dict[file_output_identifier] = max(func_evals.values())

            write_propagation_results_and_benchmark_difference_to_file(
                perturbed_dynamics_simulator, file_output_identifier, benchmark_interpolator
            )

            prop_count += 1

import numpy as np
import matplotlib.pyplot as plt
import os

figures_dir = "figures"
if not os.path.exists(figures_dir):
    os.makedirs(figures_dir)

# Data matching your simulation loops
# integration_tolerances = [1.0e-14, 1.0e-12, 1.0e-10, 1.0e-8, 1.0e-6]
# step_sizes = [2**i for i in range(3, 10)]
phase_names = ["Flyby (Callisto)", "Orbit (GCO500)"]

# Mapping indices to names and stage counts
stages_dict = {0: 6, 1: 8, 2: 13}
labels_var = {0: "Var RKF4(5)", 1: "Var RKF5(6)", 2: "Var RKF7(8)"}
labels_fix = {0: "Fixed RK4", 1: "Fixed RK6", 2: "Fixed RK8"}
colors = {0: 'blue', 1: 'green', 2: 'red'}

# =====================================================================
# Plotting 4a: Maximum Error vs Number of Function Evaluations
# =====================================================================
# Track the best file for each phase that meets 1m requirement
chosen_files = {0: None, 1: None}  # Will be automatically filled
best_evals = {0: float('inf'), 1: float('inf')}
chosen_data = {0: None, 1: None}  # Store (evals, max_err) for marking

for phase_idx in range(2):
    plt.figure(figsize=(10, 7))
    
    # 1. Variable Step Propagations
    for coeff_idx in range(3):
        evals_list = []
        max_err_list = []
        for tol_idx in range(len(integration_tolerances)):
            # Check the exact suffix generated by your helper function!
            file_name = f"SimulationOutput/Q4_variable_tolerance_index_{tol_idx}_coeff_{coeff_idx}_phase_{phase_idx}_benchmark_difference.dat"
            
            if os.path.exists(file_name):
                data = np.loadtxt(file_name)
                # Max position error
                max_err = np.max(np.linalg.norm(data[:, 1:4], axis=1))
                # Get actual function evaluations
                num_evals = func_evals_dict.get(file_name.replace("_benchmark_difference.dat", "").replace("SimulationOutput/", ""), len(data) * stages_dict[coeff_idx])
                
                max_err_list.append(max_err)
                evals_list.append(num_evals)
                
                # Track file that meets 1m with fewest evals
                if max_err < 1.0 and num_evals < best_evals[phase_idx]:
                    best_evals[phase_idx] = num_evals
                    chosen_files[phase_idx] = file_name
                    chosen_data[phase_idx] = (num_evals, max_err)
                
        if evals_list:
            plt.loglog(evals_list, max_err_list, marker='o', color=colors[coeff_idx], label=labels_var[coeff_idx])

    # 2. Fixed Step Propagations
    for coeff_idx in range(3):
        evals_list = []
        max_err_list = []
        for step_size in step_sizes:
            file_name = f"SimulationOutput/Q4_fixed_step_size_{step_size}_coeff_{coeff_idx}_phase_{phase_idx}_benchmark_difference.dat"
            
            if os.path.exists(file_name):
                data = np.loadtxt(file_name)
                max_err = np.max(np.linalg.norm(data[:, 1:4], axis=1))
                # Get actual function evaluations
                num_evals = func_evals_dict.get(file_name.replace("_benchmark_difference.dat", "").replace("SimulationOutput/", ""), len(data) * stages_dict[coeff_idx])
                
                max_err_list.append(max_err)
                evals_list.append(num_evals)
                
                # Track file that meets 1m with fewest evals
                if max_err < 1.0 and num_evals < best_evals[phase_idx]:
                    best_evals[phase_idx] = num_evals
                    chosen_files[phase_idx] = file_name
                    chosen_data[phase_idx] = (num_evals, max_err)
                
        if evals_list:
            plt.loglog(evals_list, max_err_list, marker='s', linestyle='--', color=colors[coeff_idx], alpha=0.7, label=labels_fix[coeff_idx])

    # Add marker for chosen integrator
    if chosen_data[phase_idx]:
        chosen_evals, chosen_error = chosen_data[phase_idx]
        plt.scatter(chosen_evals, chosen_error, color='gold', edgecolor='black', marker='*', s=800, 
                   zorder=5, label='Chosen Setting (<1m)', linewidth=2)
    
    # Formatting 4a
    plt.title(f"Integrator Performance: {phase_names[phase_idx]}")
    plt.xlabel("Total Number of Function Evaluations")
    plt.ylabel(r"Maximum Position Error $\epsilon_{max}$ [m]")
    
    # Plot a horizontal line indicating the 1-meter requirement
    plt.axhline(y=1.0, color='black', linestyle=':', label='1m Accuracy Requirement')
    
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='upper right', fontsize=9)
    plt.tight_layout()
    
    phase_label = "flyby" if phase_idx == 0 else "orbit"
    plt.savefig(f"{figures_dir}/Q4a_workload_diagram_{phase_label}.pdf", format='pdf', dpi=150)
    plt.close()

# =====================================================================
# Plotting 4b: Error vs Time for Chosen Integrator (Automatically Selected)
# =====================================================================
for phase_idx in range(2):
    plt.figure(figsize=(10, 6))
    file_name = chosen_files[phase_idx]
    
    if file_name and os.path.exists(file_name):
        data = np.loadtxt(file_name)
        time = data[:, 0]
        pos_error_mag = np.linalg.norm(data[:, 1:4], axis=1)
        time_hours = (time - time[0]) / 3600.0
        max_error = np.max(pos_error_mag)
        
        # Extract integrator type and parameters from filename
        if "variable" in file_name:
            tol_idx = int(file_name.split("tolerance_index_")[1].split("_")[0])
            coeff_idx = int(file_name.split("coeff_")[1].split("_")[0])
            integrator_type = f"Variable Step {labels_var[coeff_idx]}"
            param_value = f"Tolerance: {integration_tolerances[tol_idx]:.0e}"
        else:  # fixed step
            step_size = int(file_name.split("step_size_")[1].split("_")[0])
            coeff_idx = int(file_name.split("coeff_")[1].split("_")[0])
            integrator_type = f"Fixed Step {labels_fix[coeff_idx]}"
            param_value = f"Step Size: {step_size} s"
        
        plt.semilogy(time_hours, pos_error_mag, color='purple', linewidth=2)
        
        title = f"Integration Error for Chosen Setting: {phase_names[phase_idx]}\n"
        title += f"{integrator_type} | {param_value}\nMax Error: {max_error:.2e} m"
        plt.title(title, fontsize=11)
        plt.xlabel("Time [hours]")
        plt.ylabel(r"$||\epsilon_r(t)|| \approx ||r(t) - \bar{r}(t)||$ [m]")
        plt.grid(True, which="both", ls="--", alpha=0.5)
        plt.tight_layout()
        
        phase_label = "flyby" if phase_idx == 0 else "orbit"
        plt.savefig(f"{figures_dir}/Q4b_chosen_error_vs_time_{phase_label}.pdf", format='pdf', dpi=150)
        plt.close()
        
        print(f"\n{'='*70}")
        print(f"Phase {phase_idx} ({phase_names[phase_idx]}):")
        print(f"  Chosen File: {file_name}")
        print(f"  Integrator Type: {integrator_type}")
        print(f"  Parameter: {param_value}")
        print(f"  Maximum Error: {max_error:.2e} m")
        print(f"  Function Evaluations: {chosen_data[phase_idx][0]:.0f}")
        print(f"{'='*70}")
    else:
        print(f"\nPhase {phase_idx}: No integrator found that meets <1m accuracy requirement.")