import subprocess

# Run the pip freeze command and store the output in a variable
requirements = subprocess.check_output(['pip', 'freeze']).decode()

# Write the requirements to a file
with open('requirements.txt', 'w') as file:
    file.write(requirements)

# Prompt: Give me a script I can run and get a requirements.txt file I can pipe into
# a dockerfile for later use. It should override and not append to the file if it
# already exists.