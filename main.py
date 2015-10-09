import configparser

from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

from github import Github
from mixpanel import Mixpanel

from datetime import datetime
import calendar

# Using config file
def config_init():
	config = configparser.ConfigParser()

	config.read('config.ini')

	global gh 
	gh = config['github.com']
	global ga 
	ga = config['google_analytics']
	global mp 
	mp = config['mixpanel']

# Google Analytics Code
def get_service(api_name, api_version, scope, key_file_location,
                service_account_email):
  	"""Get a service that communicates to a Google API.

  	Args:
    api_name: The name of the api to connect to.
    api_version: The api version to connect to.
    scope: A list auth scopes to authorize for the application.
    key_file_location: The path to a valid service account p12 key file.
    service_account_email: The service account email address.

  	Returns:
    A service that is connected to the specified API.
  	"""

	f = open(key_file_location, 'rb')
	key = f.read()
	f.close()
	
	credentials = SignedJwtAssertionCredentials(service_account_email, key, scope=scope)

	http = credentials.authorize(httplib2.Http())

	# Build the service object.
	service = build(api_name, api_version, http=http)
	
	return service


def get_view_counts(service):
  	# Use the Analytics service object to get the first profile id.

  	# Get a list of all Google Analytics accounts for this user
  	accounts = service.management().accounts().list().execute()

  	if accounts.get('items'):
		# Get the first Google Analytics account.
		account = accounts.get('items')[0].get('id')

		# Get a list of all the properties for the first account.
		properties = service.management().webproperties().list(accountId=account).execute()

		if properties.get('items'):
			property_list = []
			property_names = []
			# Hard-coding the names and indices for the different properties
			for k, v in enumerate(properties.get('items')):
				if properties.get('items')[k].get('name') in ('LaunchDarkly Marketing', 'Tech Docs LaunchDarkly', 'API Docs LaunchDarkly', 'LaunchDarkly blog'):
					property = properties.get('items')[k].get('id')
					property_list.append(property)
					property_names.append(v.get('name'))
			
			profile_list = []
			for property in property_list:
				# Get a list of all views (profiles) for the property.
				profiles = service.management().profiles().list(accountId=account, webPropertyId=property).execute()
				if profiles.get('items'):
		        	# return a list of profile IDs.
					for key, value in enumerate(profiles.get('items')):
						profile_list.append(profiles.get('items')[key].get('id'))
			
			return (profile_list, property_names)

	return None


def get_results(service, profile_id):
	# Use the Analytics Service Object to query the Core Reporting API
	# for the number of sessions within the past seven days.
	return service.data().ga().get(
		ids='ga:' + profile_id,
		start_date='7daysAgo',
		end_date='today',
		metrics='ga:sessions').execute()

def google_analytics_main():
	# Define the auth scopes to request.
	scope = ['https://www.googleapis.com/auth/analytics.readonly']

	# Use the developer console and replace the values with your
	# service account email and relative location of your key file.
	service_account_email = ga['SERVICEACCEMAIL']
	key_file_location = ga['KEYFILELOCATION']

	# Authenticate and construct service.
	service = get_service('analytics', 'v3', scope, key_file_location, service_account_email)
	combination = get_view_counts(service)
	profiles = combination[0]
	properties = combination[1]
	total_sessions = 0
	print "\nGoogle Analytics Data\n"
	for index, profile in enumerate(profiles):
		results = get_results(service, profile)
		sessions = int(results.get('rows')[0][0])
		total_sessions += sessions
		print "Sessions from " + str(properties[index]) + ": " + str(sessions)
	print "Total Sessions: " + str(total_sessions)

def github_main():
	g = Github(gh['TOKEN'])

	stargazers = 0
	forks = 0

	for repo in g.get_organization('launchdarkly').get_repos(type='public'):
		stargazers += repo.stargazers_count
		forks += repo.forks_count

	print "\nGithub Data\n"
	print "GitHub Stargazers:", stargazers
	print "GitHub Forks:", forks
	
def mixpanel_main():
	api_client = Mixpanel(mp['APIKEY'], mp['APISECRET'])
	data = api_client.request(['events'], {
        'event' : ['create_feature', 'signup', 'add_member'],
        'unit' : 'week',
        'interval' : 1,
        'type': 'general'
    })
	date = data['data']['series'][0]
	print "Metrics for the week ending " + date + "\n"
	print "Mixpanel\n"
	print "Signups: " + str(data['data']['values']['signup'][date])
	print "Members added: " + str(data['data']['values']['add_member'][date])
	print "Created first feature: " + str(data['data']['values']['create_feature'][date])

def main():
	config_init()
	mixpanel_main()
	github_main()
	google_analytics_main()

if __name__ == '__main__':
  main()