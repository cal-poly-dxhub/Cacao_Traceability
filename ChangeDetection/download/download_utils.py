import getpass
import json
import requests
import sys
import threading
import re
import os
import glob

from botocore.exceptions import ClientError


sema = None
threads = []
path = "" # download path


""" Prompt user for API credentials. """
def get_credentials(prompt="Username: "):
    username = input(prompt)
    password = getpass.getpass("Password: ")
    return username, password


def confirm(prompt):
    resp = input(prompt).lower()
    while resp not in ['yes', 'y', 'no', 'n']:
        print("Sorry, I don't understand.")
        resp = input(prompt).lower()
    return resp.lower() in ['yes', 'y']


""" Send an HTTP POST request. """
def send_request(url, data, apiKey=None, exitIfNoResponse=True):  
    json_data = json.dumps(data)
    
    if apiKey == None:
        response = requests.post(url, json_data)
    else:
        headers = {'X-Auth-Token': apiKey}              
        response = requests.post(url, json_data, headers = headers)  
    
    try:
      httpStatusCode = response.status_code 
      if response == None:
          print("Error: No output from service")
          if exitIfNoResponse: sys.exit()
          else: return False
      output = json.loads(response.text)
      if output['errorCode'] != None:
          print(f"Error: {output['errorCode']} - {output['errorMessage']}")
          if exitIfNoResponse: sys.exit()
          else: return False
      if  httpStatusCode == 404:
          print("Error: 404 Not Found")
          if exitIfNoResponse: sys.exit()
          else: return False
      elif httpStatusCode == 401: 
          print("Error: 401 Unauthorized")
          if exitIfNoResponse: sys.exit()
          else: return False
      elif httpStatusCode == 400:
          print("Error: ", httpStatusCode)
          if exitIfNoResponse: sys.exit()
          else: return False
    except Exception as e: 
          response.close()
          print(f"Error: {e}")
          if exitIfNoResponse: sys.exit()
          else: return False
    response.close()
    
    return output['data']


""" Download a file from the specified URL. Will append to completed_list if provided. """
def download_file(url, completed_list = [], max_tries=5):
    sema.acquire()
    try:        
        response = requests.get(url, stream=True)
        disposition = response.headers['content-disposition']
        filename = re.findall("filename=(.+)", disposition)[0].strip("\"")
        print(f"Downloading {filename}...")
        if path != "" and path[-1] != "/":
            filename = "/" + filename
        open(path+filename, 'wb').write(response.content)
        print(f"Downloaded {filename}.")
        completed_list.append(filename)
        sema.release()
    except Exception as e:
        sema.release()
        print(f"Failed to download from {url}: {e}")
        if max_tries > 0:
            print("Attempting to redownload...")
            threaded_download(url, threads, completed_list, max_tries - 1)
        else:
            print("Max number of tries exceeded. Aborting...")
    
""" Download a file from the specified URL in a new thread. Will append to completed_list if provided. """    
def threaded_download(url, threads, completed_list=[], max_tries=5):
    thread = threading.Thread(target=download_file, args=(url, completed_list, max_tries))
    threads.append(thread)
    thread.start()


""" Given the name of a file on local storage, upload it to an s3 bucket then delete the local copy. """
def upload_to_s3(filename, bucket, prefix, s3, delete=False):
    try:
        key = s3_join(prefix, filename)
        print("Uploading " + filename + " to s3...")
        s3.meta.client.upload_file(Filename=filename, Bucket=bucket, Key=key)
        if delete:
            os.remove(filename)
    except ClientError as e:
        print("Error while trying to upload " + filename + ": " +  e)
    
    
""" Intelligently join objects of elements with forward slashes.
    os.path.join will use backslashes on Windows machines, which must be corrected. """
def s3_join(*elements):
    if len(elements) > 0:
        return os.path.join(*elements).replace("\\", "/")
    return ""