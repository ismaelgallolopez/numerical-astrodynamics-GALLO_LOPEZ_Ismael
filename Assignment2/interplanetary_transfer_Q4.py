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
# RUN CODE FOR QUESTION 4 #################################################
###########################################################################

if __name__ == "__main__":

    # rsw_acceleration_magnitude = [0, 0, 0]

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

    ###########################################################################
    # RUN CODE FOR QUESTION 4b ################################################
    ###########################################################################

    # Set start and end times of full trajectory
    departure_epoch_with_buffer = departure_epoch_soi
    arrival_epoch_with_buffer = arrival_epoch_soi

    # Solve for state transition matrix on current arc
    termination_settings = propagation_setup.propagator.time_termination(
        arrival_epoch_with_buffer 
    )
    variational_equations_solver = propagate_variational_equations(
        departure_epoch_with_buffer,
        termination_settings,
        bodies,
        lambert_arc_ephemeris,
        use_rsw_acceleration = True)

    sensitivity_matrix_history = variational_equations_solver.sensitivity_matrix_history
    state_history = variational_equations_solver.state_history
    lambert_history = get_lambert_arc_history(lambert_arc_ephemeris, state_history)

    r_num_final = state_history[arrival_epoch_with_buffer][0:3]
    r_lam_final = lambert_history[arrival_epoch_with_buffer][0:3]
    delta_r_final = r_lam_final - r_num_final

    final_sensitivity_matrix = sensitivity_matrix_history[arrival_epoch_with_buffer]
    S_r = final_sensitivity_matrix[0:3, :]  

    # Compute low-thrust RSW acceleration to meet required final position
    rsw_acceleration_magnitude = np.linalg.solve(S_r, delta_r_final)
    print(rsw_acceleration_magnitude) # debugging

    # Propagate dynamics with RSW acceleration. NOTE: use the rsw_acceleration_magnitude as
    # input to the propagate_trajectory function
    dynamics_simulator = propagate_trajectory(
        departure_epoch_with_buffer,
        termination_settings,
        bodies,
        lambert_arc_ephemeris,
        use_perturbations=True,
        use_rsw_acceleration=True,
        rsw_acceleration_magnitude=rsw_acceleration_magnitude,
    )

    # Extract the corrected state history
    state_history_q4 = dynamics_simulator.propagation_results.state_history
    epochs_q4 = np.array(list(state_history_q4.keys()))
    states_array_q4 = np.vstack(list(state_history_q4.values()))
    position_num_q4 = states_array_q4[:, 0:3]

    lambert_history_q4 = get_lambert_arc_history(lambert_arc_ephemeris, state_history_q4)
    lambert_array_q4 = np.vstack(list(lambert_history_q4.values()))
    position_lam_q4 = lambert_array_q4[:, 0:3]

    # Calculate deviation magnitude
    delta_r_q4 = np.linalg.norm(position_num_q4 - position_lam_q4, axis=1)
    time_days_q4 = (epochs_q4 - departure_epoch_with_buffer) / constants.JULIAN_DAY

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time_days_q4, delta_r_q4, color='teal', linewidth=2)

    ax.set_ylabel('$\\Delta r$ [m]', fontsize=12)
    ax.set_xlabel('Time since departure [days]', fontsize=12)
    ax.set_title('Continuous Low-Thrust Corrected Propagation (Question 4c)', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_yscale('log') # Log scale helps visualize the deviation growth before the forced target matching

    plt.tight_layout()
    plt.savefig("figures/Q4_b_continuous_thrust_correction.pdf", format='pdf', bbox_inches='tight')
    plt.close(fig)

    ###########################################################################
    # RUN CODE FOR QUESTION 4c ################################################
    ###########################################################################

    #arc 1
    rsw_acceleration_magnitude_1 = rsw_acceleration_magnitude
    midpoint_epoch = (departure_epoch_with_buffer + arrival_epoch_with_buffer) / 2

    termination_arc1 = propagation_setup.propagator.time_termination(midpoint_epoch)
    dynamics_arc1 = propagate_trajectory(
        departure_epoch_with_buffer,
        termination_arc1,
        bodies,
        lambert_arc_ephemeris,
        use_perturbations=True,
        use_rsw_acceleration=True,
        rsw_acceleration_magnitude=rsw_acceleration_magnitude_1,
    )
    state_history_arc1 = dynamics_arc1.propagation_results.state_history
    state_at_midpoint = state_history_arc1[midpoint_epoch]

    #arc 2
    lambert_state_at_midpoint = lambert_arc_ephemeris.cartesian_state(midpoint_epoch)
    arc2_initial_state_correction = state_at_midpoint - lambert_state_at_midpoint

    termination_arc2 = propagation_setup.propagator.time_termination(arrival_epoch_with_buffer)

    rsw_acceleration_magnitude_2 = np.zeros(3)

    var_solver_arc2 = propagate_variational_equations(
        midpoint_epoch,
        termination_arc2,
        bodies,
        lambert_arc_ephemeris,
        initial_state_correction=arc2_initial_state_correction,
        use_rsw_acceleration=True,
        rsw_acceleration_magnitude=rsw_acceleration_magnitude_2,
    )
    sh_arc2 = var_solver_arc2.state_history
    lh_arc2 = get_lambert_arc_history(lambert_arc_ephemeris, sh_arc2)
    smh_arc2 = var_solver_arc2.sensitivity_matrix_history

    pos_dev_arc2 = lh_arc2[arrival_epoch_with_buffer][0:3] - sh_arc2[arrival_epoch_with_buffer][0:3]

    # iter_count = 0 # debugging
    while np.linalg.norm(pos_dev_arc2) >= 1.0:

        S_arc2 = smh_arc2[arrival_epoch_with_buffer][0:3, :]
        delta_rsw_2 = np.linalg.solve(S_arc2, pos_dev_arc2)
        rsw_acceleration_magnitude_2 = rsw_acceleration_magnitude_2 + delta_rsw_2

        var_solver_arc2 = propagate_variational_equations(
            midpoint_epoch,
            termination_arc2,
            bodies,
            lambert_arc_ephemeris,
            initial_state_correction=arc2_initial_state_correction,
            use_rsw_acceleration=True,
            rsw_acceleration_magnitude=rsw_acceleration_magnitude_2,
        )
        sh_arc2 = var_solver_arc2.state_history
        lh_arc2 = get_lambert_arc_history(lambert_arc_ephemeris, sh_arc2)
        smh_arc2 = var_solver_arc2.sensitivity_matrix_history

        pos_dev_arc2 = lh_arc2[arrival_epoch_with_buffer][0:3] - sh_arc2[arrival_epoch_with_buffer][0:3]

        # iter_count += 1 # debugging
        # print(iter_count) # debugging

    print(rsw_acceleration_magnitude_1) # debugging
    print(rsw_acceleration_magnitude_2) # debugging
    print(np.linalg.norm(rsw_acceleration_magnitude_1)) # debugging
    print(np.linalg.norm(rsw_acceleration_magnitude_2)) # debugging

    dynamics_arc2 = propagate_trajectory(
        midpoint_epoch,
        termination_arc2,
        bodies,
        lambert_arc_ephemeris,
        use_perturbations=True,
        initial_state_correction=arc2_initial_state_correction,
        use_rsw_acceleration=True,
        rsw_acceleration_magnitude=rsw_acceleration_magnitude_2,
    )
    state_history_arc2 = dynamics_arc2.propagation_results.state_history


    # Combine the dictionaries to form the full trajectory
    full_state_history_q4c = {**state_history_arc1, **state_history_arc2}

    # Extract states and epochs
    epochs_q4c = np.array(list(full_state_history_q4c.keys()))
    states_array_q4c = np.vstack(list(full_state_history_q4c.values()))
    position_num_q4c = states_array_q4c[:, 0:3]

    lambert_history_q4c = get_lambert_arc_history(lambert_arc_ephemeris, full_state_history_q4c)
    lambert_array_q4c = np.vstack(list(lambert_history_q4c.values()))
    position_lam_q4c = lambert_array_q4c[:, 0:3]

    # Calculate deviation magnitude
    delta_r_q4c = np.linalg.norm(position_num_q4c - position_lam_q4c, axis=1)
    time_days_q4c = (epochs_q4c - departure_epoch_with_buffer) / constants.JULIAN_DAY

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the full continuous trajectory
    ax.plot(time_days_q4c, delta_r_q4c, color='purple', linewidth=2, label='Converged Two-Arc Trajectory')

    # Mark the midpoint where Arc 1 ends and Arc 2 begins
    midpoint_day = (midpoint_epoch - departure_epoch_with_buffer) / constants.JULIAN_DAY
    ax.axvline(x=midpoint_day, color='black', linestyle='--', alpha=0.5, label='Arc Boundary')

    ax.set_ylabel('$\\Delta r$ [m]', fontsize=12)
    ax.set_xlabel('Time since departure [days]', fontsize=12)
    ax.set_title('Two-Arc Continuous Low-Thrust Correction (Question 4c)', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_yscale('log')
    ax.legend()

    plt.tight_layout()
    plt.savefig("figures/Q4_c_two_arc_correction.pdf", format='pdf', bbox_inches='tight')
    plt.close(fig)

    
