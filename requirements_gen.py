import subprocess

# Run the pip freeze command and store the output in a variable
requirements = subprocess.check_output(['pip', 'freeze']).decode()

# Write the requirements to a file
with open('requirements.txt', 'w') as file:
    file.write(requirements)