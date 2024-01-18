#!/bin/python

import requests
from bs4 import BeautifulSoup as bs
#import requests_cache
import os
import time

#requests_cache.install_cache('namecheap_cache')
SANDBOX=False

api_username = "username"
api_key = "put your namecheap api key here"
client_ip = "0.0.0.0"
nc_username = "username"

def main(): 
	domain = os.getenv('CERTBOT_DOMAIN')
	records = get_host_records(domain)
	records = clean_old_challenges(records)
	records = append_challenge_tag(records)
	set_host_records(domain,records)
	time.sleep(60)

def method_url(cmd_name, *args, **kwargs):
	"""
	Transforms a method name into a request URL.
	Can return either sandbox or live URL.
	"""
	global api_username, api_key, nc_username, client_ip
	sandbox = kwargs.get('sandbox', True)
	if sandbox:
		api_url = "https://api.sandbox.namecheap.com/xml.response"
	else:
		api_url = "https://api.namecheap.com/xml.response"
	return f"{api_url}?ApiUser={api_username}&ApiKey={api_key}&UserName={nc_username}&ClientIp={client_ip}&Command={cmd_name}"

def get_host_records(domain):
	"""
	Return list of <Host> elements.
	Does not yet support mutlipart TLDs.
	"""
	url = method_url("namecheap.domains.dns.getHosts", sandbox=SANDBOX)
	[SLD, TLD] = domain.split('.')
	url = url + f"&SLD={SLD}&TLD={TLD}"
	result = requests.get(url).text
	soup = bs(result, 'lxml')
	hosts = soup.find_all('host')
	return hosts

def clean_old_challenges(records):
	"""
	Removes all old _acme-challenge TXT tags.
	Returns list of <Host> elements,
	but without any challenge tags.
	"""
	for record in records.copy():
		if record['name'] == "_acme-challenge":
			records.remove(record)
	return records

def append_challenge_tag(records):
	"""
	Generate a new challenge tag and append to records.
	Returns list of <Host> elements,
	with a new challenge tag appended.
	"""
	challenge = os.getenv('CERTBOT_VALIDATION')
	challenge_tag = bs(f'<host name="_acme-challenge" type="TXT" address="{challenge}" ttl="60"', 'lxml').body.next
	records.append(challenge_tag)
	return records

def set_host_records(domain,records):
	"""
	Updates records for domain.
	Currently only cares about name, type, address, and optional ttl.
	"""
	url = method_url("namecheap.domains.dns.setHosts", sandbox=SANDBOX)
	[SLD, TLD] = domain.split('.')
	url = url + f"&SLD={SLD}&TLD={TLD}"
	n = 1
	for record in records:
		name = record['name']
		type = record['type']
		address = record['address']
		if record['ttl']:
			ttl = record['ttl']
		url = url + f"&HostName{n}={name}&RecordType{n}={type}&Address{n}={address}"
		if ttl:
			url = url + f"&TTL{n}={ttl}"
		n += 1
	result = requests.get(url).text
	soup = bs(result, 'lxml')
	success = soup.find_all(attrs={"issuccess":"true"})
	if success:
		print("Records successfully updated.")

if __name__ == "__main__":
	main()
