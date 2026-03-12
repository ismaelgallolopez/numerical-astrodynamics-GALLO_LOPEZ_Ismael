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
import time
import datetime
import csv

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

    ###########################################################################
    # RUN CODE FOR QUESTION 4d ################################################
    ###########################################################################

    p_b = rsw_acceleration_magnitude
    std_dev = 0.4 * np.linalg.norm(p_b)

    n_monte_carlo = 1000
    monte_carlo_csv_path = os.path.join(output_directory, "q4_monte_carlo_runs.csv")
    os.makedirs(output_directory, exist_ok=True)

    if not os.path.exists(monte_carlo_csv_path):
        with open(monte_carlo_csv_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "run_idx",
                    "converged",
                    "iter_arc2",
                    "p1_r",
                    "p1_s",
                    "p1_w",
                    "p2_r",
                    "p2_s",
                    "p2_w",
                    "average_thrust",
                    "p1_deviation",
                ]
            )
        existing_rows = 0
    else:
        with open(monte_carlo_csv_path, 'r', newline='') as csv_file:
            existing_rows = sum(1 for _ in csv_file) - 1
        if existing_rows < 0:
            existing_rows = 0

    start_run = min(existing_rows, n_monte_carlo)

    mc_start_time = time.time()

    print(f"starting monte carlo from run {start_run}/{n_monte_carlo}")

    for mc_idx in range(start_run, n_monte_carlo):

        if mc_idx % 10 == 0:
            print(f"run {mc_idx}/{n_monte_carlo} (time so far: {time.time() - mc_start_time} s)")

        p1_trial = np.random.normal(loc=p_b, scale=std_dev, size=3)

        dynamics_arc1_mc = propagate_trajectory(
            departure_epoch_with_buffer,
            termination_arc1,
            bodies,
            lambert_arc_ephemeris,
            use_perturbations=True,
            use_rsw_acceleration=True,
            rsw_acceleration_magnitude=p1_trial,
        )
        state_history_arc1_mc = dynamics_arc1_mc.propagation_results.state_history
        state_mid_mc = state_history_arc1_mc[midpoint_epoch]

        lambert_state_mid_mc = lambert_arc_ephemeris.cartesian_state(midpoint_epoch)
        arc2_init_corr_mc = state_mid_mc - lambert_state_mid_mc

        p2_trial = np.zeros(3)

        var_solver_arc2_mc = propagate_variational_equations(
            midpoint_epoch,
            termination_arc2,
            bodies,
            lambert_arc_ephemeris,
            initial_state_correction=arc2_init_corr_mc,
            use_rsw_acceleration=True,
            rsw_acceleration_magnitude=p2_trial,
        )
        sh_arc2_mc = var_solver_arc2_mc.state_history
        lh_arc2_mc = get_lambert_arc_history(lambert_arc_ephemeris, sh_arc2_mc)
        smh_arc2_mc = var_solver_arc2_mc.sensitivity_matrix_history

        pos_dev_arc2_mc = (
            lh_arc2_mc[arrival_epoch_with_buffer][0:3]
            - sh_arc2_mc[arrival_epoch_with_buffer][0:3]
        )

        iter_mc = 0
        while np.linalg.norm(pos_dev_arc2_mc) >= 1.0:

            S_arc2_mc = smh_arc2_mc[arrival_epoch_with_buffer][0:3, :]
            delta_p2_mc = np.linalg.solve(S_arc2_mc, pos_dev_arc2_mc)
            p2_trial = p2_trial + delta_p2_mc

            var_solver_arc2_mc = propagate_variational_equations(
                midpoint_epoch,
                termination_arc2,
                bodies,
                lambert_arc_ephemeris,
                initial_state_correction=arc2_init_corr_mc,
                use_rsw_acceleration=True,
                rsw_acceleration_magnitude=p2_trial,
            )
            sh_arc2_mc = var_solver_arc2_mc.state_history
            lh_arc2_mc = get_lambert_arc_history(lambert_arc_ephemeris, sh_arc2_mc)
            smh_arc2_mc = var_solver_arc2_mc.sensitivity_matrix_history

            pos_dev_arc2_mc = (
                lh_arc2_mc[arrival_epoch_with_buffer][0:3]
                - sh_arc2_mc[arrival_epoch_with_buffer][0:3]
            )

            iter_mc += 1
            if iter_mc > 50:
                print('non converging monte carlo. run', mc_idx)
                break

        if iter_mc > 50:
            converged = 0
            average_thrust = np.nan
            p1_deviation = np.nan
            p2_to_write = np.array([np.nan, np.nan, np.nan])
        else:
            converged = 1
            average_thrust = (np.linalg.norm(p1_trial) + np.linalg.norm(p2_trial))/2
            p1_deviation = np.linalg.norm(p1_trial - p_b)
            p2_to_write = p2_trial.copy()

        with open(monte_carlo_csv_path, 'a', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    mc_idx,
                    converged,
                    iter_mc,
                    p1_trial[0],
                    p1_trial[1],
                    p1_trial[2],
                    p2_to_write[0],
                    p2_to_write[1],
                    p2_to_write[2],
                    average_thrust,
                    p1_deviation,
                ]
            )

    mc_raw = np.genfromtxt(
        monte_carlo_csv_path,
        delimiter=',',
        names=True,
        dtype=None,
        encoding='utf-8',
    )
    mc_raw = np.atleast_1d(mc_raw)

    converged_mask = mc_raw['converged'] == 1
    if not np.any(converged_mask):
        raise RuntimeError("No converged Monte Carlo runs found in CSV file.")

    converged_data = mc_raw[converged_mask]

    average_thrust_list = converged_data['average_thrust'].tolist()
    p1_deviation_list = converged_data['p1_deviation'].tolist()

    best_local_idx = int(np.argmin(converged_data['average_thrust']))
    best_row = converged_data[best_local_idx]
    lowest_cost = float(best_row['average_thrust'])
    best_run = int(best_row['run_idx'])
    best_p1 = np.array([best_row['p1_r'], best_row['p1_s'], best_row['p1_w']], dtype=float)
    best_p2 = np.array([best_row['p2_r'], best_row['p2_s'], best_row['p2_w']], dtype=float)

    mc_end_time = time.time()
    mc_elapsed_seconds = mc_end_time - mc_start_time
    print(f"monte carlo time: {mc_elapsed_seconds/60.0:.2f} min, average per run {mc_elapsed_seconds/n_monte_carlo} s")
    print('best run', best_run)
    print('best average thrust', lowest_cost) # what the assignment asks to plot
    print('best p1', best_p1)
    print('best p2', best_p2)

    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mc_log_path = os.path.join("monte_carlo_results.txt")
    with open(mc_log_path, 'a') as mc_log:
        mc_log.write("=" * 60 + "\n")
        mc_log.write(f"Date           : {date}\n")
        mc_log.write(f"Runs           : {n_monte_carlo}\n")
        mc_log.write(f"Elapsed        : {mc_elapsed_seconds/60.0:.2f} min\n")
        mc_log.write(f"Converged runs : {len(average_thrust_list)}\n")
        mc_log.write(f"Best avg thrust: {lowest_cost:.6e} m/s^2\n")
        mc_log.write(f"best_p1 (R,S,W): {best_p1[0]:.6e}  {best_p1[1]:.6e}  {best_p1[2]:.6e} m/s^2\n")
        mc_log.write(f"best_p2 (R,S,W): {best_p2[0]:.6e}  {best_p2[1]:.6e}  {best_p2[2]:.6e} m/s^2\n")
        mc_log.write("=" * 60 + "\n\n")

    if n_monte_carlo >= 1000: # to avoid overwriting if it is not compliant with the assignment

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.scatter(p1_deviation_list, average_thrust_list, alpha=0.6, edgecolors='w', s=40)
        
        # Optional: Plot a distinct marker for the optimum point
        best_dev = np.linalg.norm(best_p1 - p_b)
        ax.scatter(best_dev, lowest_cost, color='red', marker='*', s=200, label='Optimum Found')

        ax.set_xlabel('Deviation from initial guess $||p_1 - p^{(b)}||$ [m/s$^2$]', fontsize=12)
        ax.set_ylabel('Average Thrust $(||p_1|| + ||p_2||)/2$ [m/s$^2$]', fontsize=12)
        ax.set_title('Monte Carlo Analysis: Low-Thrust Optimization (Question 4d)', fontsize=14)
        ax.set_yscale('log')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()

        plt.tight_layout()
        plt.savefig("figures/Q4_d_monte_carlo_scatter.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig)


        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

        # Time arrays for plotting
        time_arc1_days = (np.array(list(state_history_arc1.keys())) - departure_epoch_with_buffer) / constants.JULIAN_DAY
        time_arc2_days = (np.array(list(sh_arc2.keys())) - departure_epoch_with_buffer) / constants.JULIAN_DAY
        time_full_days = np.concatenate((time_arc1_days, time_arc2_days))

        # --- Top Subplot: Baseline Model (Question 4b) ---
        # The baseline is just the constant p_b vector across the whole transfer
        ax1.plot(time_full_days, np.full_like(time_full_days, p_b[0]), label='Radial (R)', color='tab:blue')
        ax1.plot(time_full_days, np.full_like(time_full_days, p_b[1]), label='Along-track (S)', color='tab:orange')
        ax1.plot(time_full_days, np.full_like(time_full_days, p_b[2]), label='Cross-track (W)', color='tab:green')
        
        ax1.set_ylabel('Acceleration [m/s$^2$]')
        ax1.set_title('Baseline Single-Arc Thrust Profile (Question 4b)')
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend()

        # --- Bottom Subplot: Optimal Model (Question 4d) ---
        # The optimal model uses best_p1 for Arc 1 and best_p2 for Arc 2
        r_opt = np.concatenate((np.full_like(time_arc1_days, best_p1[0]), np.full_like(time_arc2_days, best_p2[0])))
        s_opt = np.concatenate((np.full_like(time_arc1_days, best_p1[1]), np.full_like(time_arc2_days, best_p2[1])))
        w_opt = np.concatenate((np.full_like(time_arc1_days, best_p1[2]), np.full_like(time_arc2_days, best_p2[2])))

        ax2.plot(time_full_days, r_opt, label='Radial (R)', color='tab:blue')
        ax2.plot(time_full_days, s_opt, label='Along-track (S)', color='tab:orange')
        ax2.plot(time_full_days, w_opt, label='Cross-track (W)', color='tab:green')
        
        midpoint_day = (midpoint_epoch - departure_epoch_with_buffer) / constants.JULIAN_DAY
        ax2.axvline(x=midpoint_day, color='black', linestyle='--', alpha=0.5, label='Arc Switch')

        ax2.set_xlabel('Time since departure [days]')
        ax2.set_ylabel('Acceleration [m/s$^2$]')
        ax2.set_title('Optimal Two-Arc Thrust Profile (Question 4d)')
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.legend()

        plt.tight_layout()
        plt.savefig("figures/Q4_d_optimal_thrust_profile.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig)
