from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from asgiref.sync import sync_to_async

import os
import subprocess
import time
from io import StringIO

import pandas
import requests

from .forms import QueryForm

# Create your views here.

def query(request):
	if request.method == 'POST':
		form = QueryForm(request.POST)
		if form.is_valid():
			# this should be the outputted data table generated by ATLAS
			# must insert an asynchronous support as the data is loaded through ATLAS so server doesn't timeout
			return HttpResponseRedirect(await sync_to_async(main_func(request), thread_sensitive=True)(pk=123))
	else:
		form = QueryForm()

	return render(request, 'query.html',{'form':form})

# Main function that will take inputted data from forms into 'atlas_query.py' script frame
# and display data

def main_func(request):
	# Should I include input text options for username and password

	RA = request.POST["RA"]
	Dec = request.POST["Dec"]
	MJD = request.POST["MJD"]
	Email = request.POST["Email"]

	BASEURL = "https://fallingstar-data.com/forcedphot"

	if os.environget("ATLASFORCED_SECRET_KEY"):
		token = os.environ.get("ATLASFORCED_SECRET_KEY")
		print("Using stored token")

	else:
		data = {"username": USR, "password": PWD}

		resp = requests.post(url=f"{BASEURL}/api-token-auth/",data=data)

		if resp.status_code == 200:
			token = resp.json()["token"]
			print(f"Your token is {token}")
			print("Store this by running/adding to your .zshrc file:")
			print(f'export ATLASFORCED_SECRET_KEY="{token}"')
		else:
			print(f"ERROR {resp.status_code}")
			print(resp.text)
			sys.exit()

	headers = {"Authorization": f"Token {token}", "Accept": "application/json"}

	task_url = None
	while not task_url:
		with requests.Session() as s:
			resp = s.post(
				f"{BASEURL}/queue/", headers=headers, data={"ra": RA, "dec": Dec, "mjd_min": MJD, "send_email": Email})

			if resp.status_code == 201:
				task_url = resp.json()["url"]
				print(f"The task url is {task_url}")
			elif resp.status_code == 429:
				message = resp.json()["detail"]
				print(f"{resp.status_code} {message}")
				t_sec = re.findall(r"available in (\d+) seconds", message)
				t_min = re.findall(r"available in (\d+) minutes", message)
				if t_sec:
					waittime = int(t_sec[0])
				elif t_min:
					waittime = int(t_min[0]) * 60
				else:
					waittime = 10
				print(f"Waiting {waittime} seconds")
				time.sleep(waittime)
			else:
				print(f"ERROR {resp.status_code}")
				print(resp.text)
				sys.exit()
	result_url = None
	taskstarted_printed = False
	while not result_url:
		with requests.Session() as s:
			resp = s.get(task_url, headers=headers)

			if resp.status_code == 200:
				if resp.json()["finishtimestamp"]:
					result_url = resp.json()["result_url"]
					print(f"Task is complete with results available at {result_url}")
				elif resp.json()["starttimestamp"]:
					if not taskstarted_printed:
						print(f"Task is running (started at {resp.json()['starttimestamp']})")
						taskstarted_printed = True
					time.sleep(2)
				else:
					print(f"Waiting for job to start (queued at {resp.json()['timestamp']})")
					time.sleep(4)
			else:
				print(f"ERROR {resp.status_code}")
				print(resp.text)
				sys.exit()
	with requests.Session () as s:
		textdata = s.get(result_url, headers=headers).text

# this is where the tom comes into play
	dfresult = pd.read_csv(StringIO(textdata.replace("###", "")), delim_whitespace=True)
	return render(request, 'query.html',{'form':form})