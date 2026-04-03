import os

from integrator_analysis_helper_functions import *

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

            write_propagation_results_and_benchmark_difference_to_file(
                perturbed_dynamics_simulator, file_output_identifier, benchmark_interpolator
            )

            prop_count += 1

