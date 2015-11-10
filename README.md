# Marketing Metrics Recorder #

## Purpose ##

Retrieve data from marketing sources and create a central place from which all API are accessed. Writes data to spreadsheets in Google Drive.

## How to use ##

 - Install Python (use Python 2.X.X)
 - Install the virtualenv package using `$ [sudo] pip install virtualenv`
 - Run `$ pip install -r requirements.txt` to download and install all dependencies:
 - Run `$ source bin/activate` to initialize virtualenv
 - Once the environment is activated, set up your config.ini file (use the example file to guide you) and run `python main.py`

## Supported metrics ##

 - Github stars across public repositories in an organization
 - Github forks across public repositories in an organization
 - Twitter followers
 - Web sessions by medium for multiple properties in Google Analytics
 - Funnels and segments in Mixpanel (delete current metrics and add your own)

## Notes ##

 - The spreadsheet writes currently included are for a specific spreadsheet setup. Ensure that the writes that are made are done for your own setups.
 - Similarly, the various dimensions and properties being drawn upon for the API calls may not match the names/dimensions you wish to use. Ensure that API calls have valid fields for your purpose.