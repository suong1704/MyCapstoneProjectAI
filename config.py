# Import necessary libraries
import os
from pathlib import Path
from dotenv import load_dotenv

# Initiate the path of our current directory using 'pathlib' module
basedir = Path(".")
# Load the environment variables containing in the .env file
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):

    # Define the Openai API Key by calling the value stored in the 'environmental variables'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')