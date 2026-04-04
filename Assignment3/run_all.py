import subprocess
import sys

scripts = [f"integrator_analysis_Q{i}.py" for i in range(1, 6)]

for script in scripts:
    print(f"--- Running {script} ---")
    result = subprocess.run([sys.executable, script])
    
    # Stop if a script fails (replicates '&&' behavior)
    if result.returncode != 0:
        print(f"Error in {script}. Halting execution.")
        break