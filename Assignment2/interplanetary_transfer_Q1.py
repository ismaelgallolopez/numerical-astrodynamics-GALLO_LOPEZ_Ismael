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

from interplanetary_transfer_helper_functions import *

# Load spice kernels.
spice.load_standard_kernels()

# Define directory where simulation output will be written
output_directory = "./SimulationOutput/"

###########################################################################
# RUN CODE FOR QUESTION 1 #################################################
###########################################################################

if __name__ == "__main__":

    # Create body objects
    bodies = create_simulation_bodies()

    # Create Lambert arc state model
    lambert_arc_ephemeris = get_lambert_problem_result(
        bodies, target_body, departure_epoch, arrival_epoch
    )

    # Create propagation settings and propagate dynamics
    termination_settings = propagation_setup.propagator.time_termination(arrival_epoch)
    dynamics_simulator = propagate_trajectory(
        departure_epoch,
        termination_settings,
        bodies,
        lambert_arc_ephemeris,
        use_perturbations=False,
    )

    # Write results to file
    write_propagation_results_to_file(
        dynamics_simulator, lambert_arc_ephemeris, "Q1", output_directory
    )

    # Extract state history from dynamics simulator
    state_history = dynamics_simulator.propagation_results.state_history

    # Evaluate the Lambert arc model at each of the epochs in the state_history
    lambert_history = get_lambert_arc_history(lambert_arc_ephemeris, state_history)


# 1. Extract data from the state history dictionaries
# The keys are epochs (seconds since J2000), values are 6x1 numpy arrays (x, y, z, vx, vy, vz)
epochs = np.array(list(state_history.keys()))
time_days = (epochs - epochs[0]) / (24 * 3600)  # Convert seconds to days for readability

# Stack the dictionary values into 2D arrays for easier slicing
num_states = np.vstack(list(state_history.values()))
lam_states = np.vstack(list(lambert_history.values()))

# Extract position components (first 3 columns)
num_x, num_y, num_z = num_states[:, 0], num_states[:, 1], num_states[:, 2]
lam_x, lam_y, lam_z = lam_states[:, 0], lam_states[:, 1], lam_states[:, 2]

# Calculate the difference for each Cartesian component
diff_x = num_x - lam_x
diff_y = num_y - lam_y
diff_z = num_z - lam_z

# 2. Plotting the total trajectory in three dimensions
fig1 = plt.figure(figsize=(10, 8))
ax1 = fig1.add_subplot(111, projection='3d')

# Plot numerical and Lambert arcs
ax1.plot(num_x, num_y, num_z, label='Numerical $x(t)$', color='blue', linestyle='-')
ax1.plot(lam_x, lam_y, lam_z, label='Lambert $\\bar{x}(t)$', color='red', linestyle='--')

# Plot the Sun at the origin
ax1.scatter([0], [0], [0], color='orange', s=100, label='Sun')

ax1.set_xlabel('X Position [m]')
ax1.set_ylabel('Y Position [m]')
ax1.set_zlabel('Z Position [m]')
ax1.set_title('Unperturbed Interplanetary Transfer Trajectory')
ax1.legend()

# 3. Plotting the difference in Cartesian position components
fig2, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

# Plot delta X
axs[0].plot(time_days, diff_x, color='purple')
axs[0].set_ylabel('$\\Delta$X [m]')
axs[0].grid(True, linestyle=':')

# Plot delta Y
axs[1].plot(time_days, diff_y, color='green')
axs[1].set_ylabel('$\\Delta$Y [m]')
axs[1].grid(True, linestyle=':')

# Plot delta Z
axs[2].plot(time_days, diff_z, color='teal')
axs[2].set_ylabel('$\\Delta$Z [m]')
axs[2].set_xlabel('Time since departure [days]')
axs[2].grid(True, linestyle=':')

fig2.suptitle('Difference Between Numerical Propagation and Lambert Targeter')
plt.tight_layout()

# Save figures as PDF files in a dedicated folder.
figures_directory = "./figures/"
os.makedirs(figures_directory, exist_ok=True)
fig1.savefig(figures_directory + "Q1_trajectory_3d.pdf", format="pdf", bbox_inches="tight")
fig2.savefig(figures_directory + "Q1_cartesian_differences.pdf", format="pdf", bbox_inches="tight")
