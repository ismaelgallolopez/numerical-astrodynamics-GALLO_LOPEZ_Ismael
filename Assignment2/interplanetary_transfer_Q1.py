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
# spice.load_standard_kernels()

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


###########################################################################
# PLOTTING RESULTS ########################################################
###########################################################################

# 1. Extract data from the state history dictionaries
epochs = np.array(list(state_history.keys()))
time_days = (epochs - epochs[0]) / (24 * 3600)  # Convert seconds to days for readability

num_states = np.vstack(list(state_history.values()))
lam_states = np.vstack(list(lambert_history.values()))

num_x, num_y, num_z = num_states[:, 0], num_states[:, 1], num_states[:, 2]
lam_x, lam_y, lam_z = lam_states[:, 0], lam_states[:, 1], lam_states[:, 2]

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

# --- PROJECTIONS ON CARTESIAN PLANES ---
# Find the min/max boundaries to draw the "walls" of the 3D plot
min_x = min(num_x.min(), lam_x.min(), 0)
max_x = max(num_x.max(), lam_x.max(), 0)
min_y = min(num_y.min(), lam_y.min(), 0)
max_y = max(num_y.max(), lam_y.max(), 0)
min_z = min(num_z.min(), lam_z.min(), 0)
max_z = max(num_z.max(), lam_z.max(), 0)

# Lock the axes limits so the projections sit flush against the bounding box
ax1.set_xlim([min_x, max_x])
ax1.set_ylim([min_y, max_y])
ax1.set_zlim([min_z, max_z])

# XY Plane Projection (Project down to the "floor" where Z = min_z)
ax1.plot(num_x, num_y, zs=min_z, zdir='z', color='blue', alpha=0.2, linestyle='-')
ax1.plot(lam_x, lam_y, zs=min_z, zdir='z', color='red', alpha=0.2, linestyle='--')

# XZ Plane Projection (Project back to the "wall" where Y = max_y)
ax1.plot(num_x, num_z, zs=max_y, zdir='y', color='blue', alpha=0.2, linestyle='-')
ax1.plot(lam_x, lam_z, zs=max_y, zdir='y', color='red', alpha=0.2, linestyle='--')

# YZ Plane Projection (Project left to the "wall" where X = min_x)
ax1.plot(num_y, num_z, zs=min_x, zdir='x', color='blue', alpha=0.2, linestyle='-')
ax1.plot(lam_y, lam_z, zs=min_x, zdir='x', color='red', alpha=0.2, linestyle='--')
# ---------------------------------------

ax1.set_xlabel('X Position [m]', labelpad=15, fontsize=16)
ax1.set_ylabel('Y Position [m]', labelpad=15, fontsize=16)
ax1.set_zlabel('Z Position [m]', labelpad=10, fontsize=16)
ax1.legend(fontsize=16)

fig1.subplots_adjust(left=0.0, right=0.85)
plt.tight_layout()

# 3. Plotting the difference in Cartesian position components
fig2, axs = plt.subplots(3, 1, figsize=(10, 6), sharex=True)

# Plot delta X
axs[0].plot(time_days, diff_x, color='purple')
axs[0].set_ylabel('$\\Delta$X [m]', fontsize=16)
axs[0].tick_params(axis='both', labelsize=13)
axs[0].grid(True, linestyle='--')

# Plot delta Y
axs[1].plot(time_days, diff_y, color='green')
axs[1].set_ylabel('$\\Delta$Y [m]', fontsize=16)
axs[1].tick_params(axis='both', labelsize=13)
axs[1].grid(True, linestyle='--')

# Plot delta Z
axs[2].plot(time_days, diff_z, color='teal')
axs[2].set_ylabel('$\\Delta$Z [m]', fontsize=16)
axs[2].set_xlabel('Time since departure [days]', fontsize=16)
axs[2].tick_params(axis='both', labelsize=13)
axs[2].grid(True, linestyle='--')

# axs[2].set_xlim([time_days[0], time_days[-1]])

# fig2.suptitle('Difference Between Numerical Propagation and Lambert Targeter')
plt.tight_layout()

# Save figures as PDF files in a dedicated folder.
figures_directory = "./figures/"
os.makedirs(figures_directory, exist_ok=True)
fig1.savefig(figures_directory + "Q1_trajectory_3d.pdf", format="pdf", bbox_inches="tight", pad_inches=0.4)
fig2.savefig(figures_directory + "Q1_cartesian_differences.pdf", format="pdf", bbox_inches="tight")


###########################################################################
# SAVING RESULTS ##########################################################
###########################################################################

save_output_to_file(0, 'Q1', state=0)
save_output_to_file(1, 'Q1', state=-1)
