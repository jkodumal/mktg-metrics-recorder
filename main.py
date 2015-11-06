import configparser

from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools

from github import Github
from mixpanel import Mixpanel

from datetime import datetime, date
import calendar

import json
import gspread

from birdy.twitter import AppClient

# Using config file
def config_init():
	config = configparser.ConfigParser()

	config.read('config.ini')

	global gh 
	global ga
	global mp 
	global gap
	global gspr
	global gsw
	global tw

	gh = config['github.com']
	ga = config['google_analytics']
	mp = config['mixpanel']
	gap = config['google_analytics_properties']
	gspr = config['google_spreadsheets']
	gsw = config['google_spreadsheets_worksheets']
	tw = config['twitter.com']

def github_main():
	g = Github(gh['TOKEN'])

	global stargazers
	global forks
	stargazers = 0
	forks = 0

	for repo in g.get_organization('launchdarkly').get_repos(type='public'):
		stargazers += repo.stargazers_count
		forks += repo.forks_count

	print "\nGithub Data\n"
	print "GitHub Stargazers:", stargazers
	print "GitHub Forks:", forks

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
				if properties.get('items')[k].get('name') in (gap['1'], gap['2'], gap['3'], gap['4']):
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
		metrics='ga:sessions',
		dimensions='ga:medium').execute()

def get_monthly_results(service, profile_id):
	# Use the Analytics Service Object to query the Core Reporting API
	# for the number of sessions within the past thirty days.
	if date.today().month in ("1", "5", "7", "8", "10", "12"):
		return service.data().ga().get(
			ids='ga:' + profile_id,
			start_date='31daysAgo',
			end_date='yesterday',
			metrics='ga:sessions',
			dimensions='ga:medium').execute()
	elif date.today().month == "3" and (date.today().year % 4 != 0):
		return service.data().ga().get(
			ids='ga:' + profile_id,
			start_date='29daysAgo',
			end_date='yesterday',
			metrics='ga:sessions',
			dimensions='ga:medium').execute()
	elif date.today().month == "3" and (date.today().year % 4 == 0):
		return service.data().ga().get(
			ids='ga:' + profile_id,
			start_date='30daysAgo',
			end_date='yesterday',
			metrics='ga:sessions',
			dimensions='ga:medium').execute()
	else:
		return service.data().ga().get(
			ids='ga:' + profile_id,
			start_date='32daysAgo',
			end_date='yesterday',
			metrics='ga:sessions',
			dimensions='ga:medium').execute()

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

	global total_direct
	global total_organic
	global total_referral
	global total_social
	global total_other
	global total_monthly

	total_direct = 0
	total_organic = 0
	total_referral = 0
	total_social = 0
	total_other = 0
	total_monthly = 0

	weekly_sessions = 0
	weekly_direct = 0
	weekly_organic = 0
	weekly_referral = 0
	weekly_social = 0
	weekly_other = 0

	print "\nGoogle Analytics Sessions\n"
	for index, profile in enumerate(profiles):
		local_sessions = 0
		local_direct = 0
		local_organic = 0
		local_referral = 0
		local_social = 0
		local_other = 0
		results = get_results(service, profile)
		monthly_results = get_monthly_results(service, profile)
		print str(properties[index])

		#Filter into each traffic source channel
		for item in results.get('rows'):
			source = item[0].lower()
			if source == '(none)':
				local_direct += int(item[1])
				weekly_direct += int(item[1])
			elif source == 'organic':
				local_organic += int(item[1])
				weekly_organic += int(item[1])
			elif source == 'referral':
				local_referral += int(item[1])
				weekly_referral += int(item[1])
			elif source == "social":
				local_social += int(item[1])
				weekly_social += int(item[1])
			else:
				local_other += int(item[1])
				weekly_other += int(item[1])

			local_sessions += int(item[1])
			weekly_sessions += int(item[1])

		print "    Direct: " + str(local_direct)
		print "    Organic: " + str(local_organic)
		print "    Referral: " + str(local_referral)
		print "    Social: " + str(local_social)
		print "    Other including Email: " + str(local_other)
		print "    Total: " + str(local_sessions) + "\n"

		#Filter into each traffic source channel
		for item in monthly_results.get('rows'):
			source = item[0].lower()
			if source == '(none)':
				total_direct += int(item[1])
			elif source == 'organic':
				total_organic += int(item[1])
			elif source == 'referral':
				total_referral += int(item[1])
			elif source == "social":
				total_social += int(item[1])
			else:
				total_other += int(item[1])

			total_monthly += int(item[1])

	print "Total Direct: " + str(weekly_direct)
	print "Total Organic: " + str(weekly_organic)
	print "Total Referral: " + str(weekly_referral)
	print "Total Social: " + str(weekly_social)
	print "Total Other including Email: " + str(weekly_other)
	print "Total Google Analytics Sessions: " + str(weekly_sessions)
	
def mixpanel_main():
	api_client = Mixpanel(mp['APIKEY'], mp['APISECRET'])
	data = api_client.request(['events'], {
        'event' : ['create_feature', 'signup', 'add_member'],
        'unit' : 'week',
        'interval' : 2,
        'type': 'general'
    })
	date = data['data']['series'][0]
	print "Metrics for the week\n"
	print "Mixpanel\n"
	global mp_signups
	global mp_members
	global mp_features
	mp_signups = data['data']['values']['signup'][date]
	mp_members = data['data']['values']['add_member'][date]
	mp_features = data['data']['values']['create_feature'][date]
	print "Signups: " + str(mp_signups)
	print "Members added: " + str(mp_members)
	print "Created first feature: " + str(mp_features)

def twitter_main():
	client = AppClient(tw['APIKEY'],tw['APISECRET'])
	access_token = client.get_access_token()
	response = client.api.users.show.get(screen_name = 'LaunchDarkly')

	global twitter_followers_count
	twitter_followers_count = response.data.followers_count
	print "\nTwitter\n"
	print "Followers: " + str(twitter_followers_count)

def spreadsheet_auth():
	json_key = json.load(open(gspr['OAUTH2JSONFILE']))
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
	gs = gspread.authorize(credentials)
	return gs

def weekly_ss_recorder(client):
	
	print 'Writing to "Metrics > ' + gsw['3'] + '" spreadsheet...'
	sheet_file = client.open_by_url(gspr['SPREADSHEETURL'])
	ws = sheet_file.worksheet(gsw['3'])
	row = ws.find("Date").row
	row_values = ws.row_values(row)
	column = len(row_values) + 1
	today = date.today()
	ws.update_cell(row, column, today)
	ws.update_cell(row + 1, column, total_sessions)
	ws.update_cell(row + 2, column, mp_signups)
	ws.update_cell(row + 3, column, mp_members)
	ws.update_cell(row + 4, column, mp_features)
	print 'Finished'

def monthly_ss_recorder(client):

	print 'Writing to "Metrics > ' + gsw['1'] + '" spreadsheet...'
	sheet_file = client.open_by_url(gspr['SPREADSHEETURL'])
	ws2 = sheet_file.worksheet(gsw['1'])
	start_row = ws2.find("Direct").row
	column = len(ws2.row_values(start_row)) + 1
	ws2.update_cell(start_row, column, total_direct)
	ws2.update_cell(start_row + 1, column, total_referral)
	ws2.update_cell(start_row + 2, column, total_organic)
	ws2.update_cell(start_row + 3, column, total_social)
	ws2.update_cell(start_row + 4, column, total_other)
	ws2.update_cell(start_row + 5, column, total_monthly)
	print 'Moving to "Metrics > ' + gsw['2'] + '" ...'
	
	print 'Writing to "Metrics > ' + gsw['2'] + '" spreadsheet...'
	ws3 = sheet_file.worksheet(gsw['2'])
	date_row = ws3.find("Date").row
	date_column = len(ws3.row_values(date_row)) + 1
	ws3.update_cell(date_row, date_column, date.today())
	tw_row = ws3.find("Twitter followers").row
	tw_column = len(ws3.row_values(tw_row)) + 1
	ws3.update_cell(tw_row, tw_column, twitter_followers_count)
	gh_row = ws3.find("Github stargazers").row
	gh_column = len(ws3.row_values(gh_row)) + 1
	ws3.update_cell(gh_row, gh_column, stargazers)
	ws3.update_cell(gh_row + 1, gh_column, forks)
	print 'Finished'

def main():

	# Default returns information from the last week
	config_init()
	mixpanel_main()
	twitter_main() # Twitter information doesn't change week to week
	github_main() # Github information doesn't change week to week
	google_analytics_main()
	if (date.isoweekday(date.today()) == 7) or (date.isoweekday(date.today()) == 1):
		client = spreadsheet_auth()
		weekly_ss_recorder(client)
	if (date.today().day == 1):
		client = spreadsheet_auth()
		monthly_ss_recorder(client)

if __name__ == '__main__':
  main()