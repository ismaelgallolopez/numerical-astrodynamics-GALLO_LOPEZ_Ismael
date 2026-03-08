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

departure_epoch_lambert = departure_epoch
arrival_epoch_lambert = arrival_epoch

###########################################################################
# RUN CODE FOR QUESTION 2 #################################################
###########################################################################

if __name__ == "__main__":

    # Create body objects
    bodies = create_simulation_bodies()

    # Create Lambert arc state model
    lambert_arc_ephemeris = get_lambert_problem_result(
        bodies, target_body, departure_epoch_lambert, arrival_epoch_lambert
    )

    # print(lambert_arc_ephemeris)
    # print(departure_epoch_lambert) # debugging
    # print(environment.Ephemeris.cartesian_position(lambert_arc_ephemeris, departure_epoch_lambert)) # debugging

    """
    case_i: The initial and final propagation time equal to the initial and final times of the Lambert arc.
    case_ii: The initial and final propagation time shifted forward and backward in time, respectively, by ∆t=1 hour.
    case_iii: The initial and final propagation time shifted forward and backward in time, respectively, by ∆t such that we start/end on the sphere of influence
    case_iv: The initial and final propagation time shifted forward and backward in time, respectively, by ∆t=1 hour. The propagation is started from the middle point in time of the Lambert arc and propagated forward and backward in time.

    """
    # List cases to iterate over. STUDENT NOTE: feel free to modify if you see fit
    cases = ["case_i", "case_ii", "case_iii", "case_iv"]

    # Run propagation for each of cases i-iii
    for i, case in enumerate(cases):
        print(case, i) # debugging

        # Define the initial and final propagation time for the current case
        
        if i == 0: 
            departure_epoch = departure_epoch_lambert
            # print(departure_epoch_lambert) # debugging
            arrival_epoch = arrival_epoch_lambert
            termination_settings = propagation_setup.propagator.time_termination(arrival_epoch)
        if i == 1:
            departure_epoch = departure_epoch_lambert - 3600
            # print(departure_epoch_lambert) # debugging
            arrival_epoch = arrival_epoch_lambert + 3600
            termination_settings = propagation_setup.propagator.time_termination(arrival_epoch)
        if i == 2: 
            departure_epoch = departure_epoch_lambert - 3600
            # print(departure_epoch_lambert) # debugging
            arrival_epoch = arrival_epoch_lambert + 3600
            termination_settings = propagation_setup.propagator.time_termination(arrival_epoch)
            # print(type(bodies)) # debugging
            # gravitational parameters of all bodies
            mu_earth = bodies.get('Earth').gravitational_parameter
            mu_venus = bodies.get('Venus').gravitational_parameter
            mu_sun = bodies.get('Sun').gravitational_parameter
            

            epochs = np.arange(departure_epoch, arrival_epoch, fixed_step_size)
            for epoch in epochs: 
                # approximate SMA of bodies required
                position_earth = bodies.get('Earth').ephemeris.cartesian_position(epoch)
                position_venus = bodies.get('Venus').ephemeris.cartesian_position(epoch)
                
                # # print(state_earth) # debugging
                # sma_earth1 = element_conversion.cartesian_to_keplerian(state_earth, mu_sun)[0]
                # # print(sma_earth) # debugging
                # sma_venus1 = element_conversion.cartesian_to_keplerian(state_venus, mu_sun)[0]

                # # different way of calculating -->check forum
                sma_earth = np.linalg.norm(position_earth)
                # print(sma_earth1) # debugging
                sma_venus = np.linalg.norm(position_venus)

                # sphere of influence radius for each body
                r_soi_earth = sma_earth*(mu_earth/mu_sun)**0.4
                r_soi_venus = sma_venus*(mu_venus/mu_sun)**0.4

                sc_position = lambert_arc_ephemeris.cartesian_position(epoch)
                if np.linalg.norm(sc_position - position_earth) > r_soi_earth:
                    departure_epoch = epoch-fixed_step_size
                    break
                # if np.linalg.norm(sc_position - position_venus) < r_soi_venus:
                #     arrival_epoch = epoch

            # hybrid termination settings
            epoch_termination_settings = propagation_setup.propagator.time_termination(arrival_epoch_lambert)

            termination_variable = propagation_setup.dependent_variable.relative_distance(
                'Spacecraft', 'Venus'
            )
            distance_termination_settings = propagation_setup.propagator.dependent_variable_termination(
                dependent_variable_settings=termination_variable,
                limit_value = r_soi_venus,
                use_as_lower_limit=True,
            )

            termination_settings_list = [
                epoch_termination_settings,
                distance_termination_settings
            ]

            termination_settings = propagation_setup.propagator.hybrid_termination(
                termination_settings_list, fulfill_single_condition=True
            )

        if i == 3:
            initial_epoch = departure_epoch_lambert - 3600
            final_epoch = arrival_epoch_lambert + 3600
            
            departure_epoch = (departure_epoch_lambert + arrival_epoch_lambert) / 2

            termination_settings = propagation_setup.propagator.non_sequential_termination(
                forward_termination_settings=propagation_setup.propagator.time_termination(final_epoch),
                backward_termination_settings=propagation_setup.propagator.time_termination(initial_epoch),
            )

        # Perform propagation
        dynamics_simulator = propagate_trajectory(
            departure_epoch,
            termination_settings,
            bodies,
            lambert_arc_ephemeris,
            use_perturbations=True,
        )
        
        

        write_propagation_results_to_file(
            dynamics_simulator,
            lambert_arc_ephemeris,
            "Q2_" + str(cases.index(case)),
            output_directory,
        )

        state_history = dynamics_simulator.propagation_results.state_history
        lambert_history = get_lambert_arc_history(lambert_arc_ephemeris, state_history)
