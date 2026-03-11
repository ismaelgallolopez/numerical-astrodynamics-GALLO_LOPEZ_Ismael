""" 
Copyright (c) 2010-2020, Delft University of Technology
All rigths reserved

This file is part of the Tudat. Redistribution and use in source and 
binary forms, with or without modification, are permitted exclusively
under the terms of the Modified BSD license. You should have received
a copy of the license with this file. If not, please or visit:
http://tudat.tudelft.nl/LICENSE.
"""

from interplanetary_transfer_helper_functions import *

# Load spice kernels.
spice.load_standard_kernels()

# Define directory where simulation output will be written
output_directory = "./SimulationOutput/"

###########################################################################
# RUN CODE FOR QUESTION 3 #################################################
###########################################################################

if __name__ == "__main__":

    # Create body objects
    bodies = create_simulation_bodies()

    # Create Lambert arc state model
    lambert_arc_ephemeris = get_lambert_problem_result(
        bodies, target_body, departure_epoch, arrival_epoch
    )
    mu_sun = bodies.get('Sun').gravitational_parameter
    mu_earth = bodies.get('Earth').gravitational_parameter
    mu_venus = bodies.get('Venus').gravitational_parameter
    
    departure_epoch_soi = departure_epoch
    search_start = departure_epoch
    search_end = arrival_epoch
    epochs_search = np.arange(search_start, search_end, fixed_step_size)
    
    for epoch in epochs_search:
        state_earth = bodies.get('Earth').ephemeris.cartesian_state(epoch)
        sma_earth = element_conversion.cartesian_to_keplerian(state_earth, mu_sun)[0]
        r_soi_earth = sma_earth * (mu_earth / mu_sun) ** 0.4
        
        position_earth = bodies.get('Earth').ephemeris.cartesian_position(epoch)
        sc_position = lambert_arc_ephemeris.cartesian_position(epoch)
        
        if np.linalg.norm(sc_position - position_earth) > r_soi_earth:
            departure_epoch_soi = epoch - fixed_step_size
            break
    
    arrival_epoch_soi = arrival_epoch
    for epoch in reversed(epochs_search):
        state_venus = bodies.get('Venus').ephemeris.cartesian_state(epoch)
        sma_venus = element_conversion.cartesian_to_keplerian(state_venus, mu_sun)[0]
        r_soi_venus = sma_venus * (mu_venus / mu_sun) ** 0.4
        
        position_venus = bodies.get('Venus').ephemeris.cartesian_position(epoch)
        sc_position = lambert_arc_ephemeris.cartesian_position(epoch)
        
        if np.linalg.norm(sc_position - position_venus) > r_soi_venus:
            arrival_epoch_soi = epoch + fixed_step_size
            break
    
    time_of_flight_soi = arrival_epoch_soi - departure_epoch_soi
    
    ##############################################################
    # Compute number of arcs and arc length
    number_of_arcs = 10
    arc_length = time_of_flight_soi / number_of_arcs

    ##############################################################

    # Store each arc state history for Q3(a) trajectory plotting
    all_state_histories_q3a = []
    # Store each corrected arc state history for Q3(c) trajectory plotting
    all_state_histories_q3c = []
    # Store each iteratively corrected arc state history for Q3(d)
    all_state_histories_q3d = []
    # Store number of correction iterations per arc for Q3(d)
    q3d_iteration_counts = []
    # Store total velocity correction norm per arc for Q3(d)
    q3d_total_delta_v_norms = []

    # Compute relevant parameters (dynamics, state transition matrix, Delta V) for each arc
    for arc_index in range(number_of_arcs):

        # Compute initial and final time for arc
        current_arc_initial_time = departure_epoch_soi + arc_index * arc_length
        current_arc_final_time = current_arc_initial_time + arc_length

        ###########################################################################
        # RUN CODE FOR QUESTION 3a ################################################
        ###########################################################################

        # Propagate dynamics on current arc (use propagate_trajectory function)
        if arc_index == number_of_arcs - 1:
            state_venus = bodies.get('Venus').ephemeris.cartesian_state(current_arc_final_time)
            sma_venus = element_conversion.cartesian_to_keplerian(state_venus, mu_sun)[0]
            r_soi_venus = sma_venus * (mu_venus / mu_sun) ** 0.4
            
            epoch_termination = propagation_setup.propagator.time_termination(current_arc_final_time)
            termination_variable = propagation_setup.dependent_variable.relative_distance(
                'Spacecraft', 'Venus'
            )
            distance_termination = propagation_setup.propagator.dependent_variable_termination(
                dependent_variable_settings=termination_variable,
                limit_value=r_soi_venus,
                use_as_lower_limit=True,
            )
            termination_settings_arc = propagation_setup.propagator.hybrid_termination(
                [epoch_termination, distance_termination], 
                fulfill_single_condition=True
            )
        else:
            termination_settings_arc = propagation_setup.propagator.time_termination(
                current_arc_final_time
            )
            
        dynamics_simulator_arc = propagate_trajectory(
            current_arc_initial_time,
            termination_settings_arc,
            bodies,
            lambert_arc_ephemeris,
            use_perturbations=True,
        )
        all_state_histories_q3a.append(
            dynamics_simulator_arc.propagation_results.state_history
        )

        ###########################################################################
        # RUN CODE FOR QUESTION 3c/d/e ############################################
        ###########################################################################
        # Note: for question 3e, part of the code below will be put into a loop
        # for the requested iterations

        # Solve for state transition matrix on current arc
        if arc_index == number_of_arcs - 1:
            state_venus = bodies.get('Venus').ephemeris.cartesian_state(current_arc_final_time)
            sma_venus = element_conversion.cartesian_to_keplerian(state_venus, mu_sun)[0]
            r_soi_venus = sma_venus * (mu_venus / mu_sun) ** 0.4
            
            epoch_termination = propagation_setup.propagator.time_termination(current_arc_final_time)
            termination_variable = propagation_setup.dependent_variable.relative_distance(
                'Spacecraft', 'Venus'
            )
            distance_termination = propagation_setup.propagator.dependent_variable_termination(
                dependent_variable_settings=termination_variable,
                limit_value=r_soi_venus,
                use_as_lower_limit=True,
            )
            termination_settings = propagation_setup.propagator.hybrid_termination(
                [epoch_termination, distance_termination], 
                fulfill_single_condition=True
            )
        else:
            termination_settings = propagation_setup.propagator.time_termination(
                current_arc_final_time
            )
            
        variational_equations_solver = propagate_variational_equations(
            current_arc_initial_time,
            termination_settings,
            bodies,
            lambert_arc_ephemeris,
        )
        state_transition_matrix_history = (
            variational_equations_solver.state_transition_matrix_history
        )
        state_history = variational_equations_solver.state_history
        lambert_history = get_lambert_arc_history(lambert_arc_ephemeris, state_history)

        # Get final state transition matrix (and its inverse)
        final_epoch = list(state_transition_matrix_history.keys())[-1]
        final_state_transition_matrix = state_transition_matrix_history[final_epoch]

        # Retrieve final state deviation
        final_state_deviation = (
            state_history[final_epoch] - lambert_history[final_epoch]
        )

        # Compute required velocity change at beginning of arc to meet required final state
        phi_rv = final_state_transition_matrix[0:3, 3:6]
        final_position_deviation = final_state_deviation[0:3]
        delta_v0 = -np.linalg.solve(phi_rv, final_position_deviation)
        initial_state_correction = np.hstack((np.zeros(3), delta_v0))

        # Propagate with correction to initial state (use propagate_trajectory function),
        # and its optional initial_state_correction input
        dynamics_simulator = propagate_trajectory(
            current_arc_initial_time,
            termination_settings,
            bodies,
            lambert_arc_ephemeris,
            use_perturbations=True,
            initial_state_correction=initial_state_correction,
        )
        all_state_histories_q3c.append(
            dynamics_simulator.propagation_results.state_history
        )

        ###########################################################################
        # RUN CODE FOR QUESTION 3d ################################################
        ###########################################################################

        total_delta_v = np.zeros(3)
        iteration_count = 0

        final_state_transition_matrix_d = final_state_transition_matrix
        final_position_deviation_d = final_position_deviation
        final_state_history_q3d = dynamics_simulator_arc.propagation_results.state_history

        print('new arc') # debugging
        while np.linalg.norm(final_position_deviation_d) >= 1.0:

            phi_rv_d = final_state_transition_matrix_d[0:3, 3:6]
            delta_v_increment = -np.linalg.solve(phi_rv_d, final_position_deviation_d)
            total_delta_v += delta_v_increment

            initial_state_correction_d = np.hstack((np.zeros(3), total_delta_v))

            variational_equations_solver_d = propagate_variational_equations(
                current_arc_initial_time,
                termination_settings,
                bodies,
                lambert_arc_ephemeris,
                initial_state_correction=initial_state_correction_d,
            )

            state_transition_matrix_history_d = (
                variational_equations_solver_d.state_transition_matrix_history
            )
            state_history_d = variational_equations_solver_d.state_history
            lambert_history_d = get_lambert_arc_history(lambert_arc_ephemeris, state_history_d)

            final_epoch_d = list(state_transition_matrix_history_d.keys())[-1]
            final_state_transition_matrix_d = state_transition_matrix_history_d[final_epoch_d]

            final_state_deviation_d = (
                state_history_d[final_epoch_d] - lambert_history_d[final_epoch_d]
            )
            final_position_deviation_d = final_state_deviation_d[0:3]
            print(np.linalg.norm(final_position_deviation_d)) # debugging

            dynamics_simulator_d = propagate_trajectory(
                current_arc_initial_time,
                termination_settings,
                bodies,
                lambert_arc_ephemeris,
                use_perturbations=True,
                initial_state_correction=initial_state_correction_d,
            )
            final_state_history_q3d = dynamics_simulator_d.propagation_results.state_history

            iteration_count += 1

        all_state_histories_q3d.append(final_state_history_q3d)
        q3d_iteration_counts.append(iteration_count)
        q3d_total_delta_v_norms.append(np.linalg.norm(total_delta_v))

    fig, ax = plt.subplots(figsize=(10, 6))

    # Iterate through` each arc's saved state history
    for i, arc_state_history in enumerate(all_state_histories_q3a):
        
        # Extract numerical epochs and states
        epochs = np.array(list(arc_state_history.keys()))
        states_array = np.vstack(list(arc_state_history.values()))
        position_num = states_array[:, 0:3]
        
        # Evaluate the Lambert arc at these exact epochs
        lambert_history = get_lambert_arc_history(lambert_arc_ephemeris, arc_state_history)
        lambert_array = np.vstack(list(lambert_history.values()))
        position_lam = lambert_array[:, 0:3]
        
        # Calculate position deviation magnitude
        delta_r = np.linalg.norm(position_num - position_lam, axis=1)
        
        # Convert time to days for the x-axis
        time_days = (epochs - departure_epoch_soi) / constants.JULIAN_DAY
        
        # Plot this specific arc (alternating colors can help visualize the discontinuities)
        color = 'blue' if i % 2 == 0 else 'orange'
        ax.plot(time_days, delta_r, color=color, linewidth=1.5, label=f'Arc {i}' if i < 2 else "")

    ax.set_ylabel('$\\Delta r$ [m]', fontsize=12)
    ax.set_xlabel('Time since departure [days]', fontsize=12)
    ax.set_title('Discontinuous Uncorrected Arc Propagation (Question 3a)', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_yscale('log') # Log scale is highly recommended to see the start of each arc!

    # Create a custom legend to just show the alternating color logic
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(['Even Arcs', 'Odd Arcs'])

    plt.tight_layout()
    plt.savefig("figures/Q3_a_discontinuous_trajectory.pdf", format='pdf', bbox_inches='tight')
    plt.close(fig)


    fig, ax = plt.subplots(figsize=(10, 6))

    for i, arc_state_history in enumerate(all_state_histories_q3c):
        
        epochs = np.array(list(arc_state_history.keys()))
        states_array = np.vstack(list(arc_state_history.values()))
        position_num = states_array[:, 0:3]
        
        lambert_history = get_lambert_arc_history(lambert_arc_ephemeris, arc_state_history)
        lambert_array = np.vstack(list(lambert_history.values()))
        position_lam = lambert_array[:, 0:3]
        
        delta_r = np.linalg.norm(position_num - position_lam, axis=1)
        # print(delta_r[-1]) # debugging
        
        time_days = (epochs - departure_epoch_soi) / constants.JULIAN_DAY
        
        color = 'green' if i % 2 == 0 else 'purple'
        ax.plot(time_days, delta_r, color=color, linewidth=1.5, label=f'Arc {i}' if i < 2 else "")

    ax.set_ylabel('$\\Delta r$ [m]', fontsize=12)
    ax.set_xlabel('Time since departure [days]', fontsize=12)
    ax.set_title('One-Shot Corrected Arc Propagation (Question 3c)', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_yscale('log') 

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(['Even Arcs (Corrected)', 'Odd Arcs (Corrected)'])

    plt.tight_layout()
    plt.savefig("figures/Q3_c_single_correction.pdf", format='pdf', bbox_inches='tight')
    plt.close(fig)