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
