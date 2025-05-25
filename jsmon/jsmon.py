#!/usr/bin/env python3

import requests
import re
import os
import hashlib
import json
import difflib
import jsbeautifier
from decouple import config

DISCORD_WEBHOOK = config("JSMON_DISCORD_WEBHOOK", default="CHANGEME")

def is_valid_endpoint(endpoint):
    regex = re.compile(r'^(?:http|ftp)s?://(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, endpoint) is not None

def get_endpoint_list(endpointdir):
    endpoints = []
    filenames = [f for f in os.listdir(endpointdir) if not f.startswith('.')]
    for file in filenames:
        with open(f"{endpointdir}/{file}", "r") as f:
            endpoints.extend(f.readlines())
    return [x.strip() for x in endpoints]

def get_endpoint(endpoint):
    return requests.get(endpoint).text

def get_hash(string):
    return hashlib.md5(string.encode("utf8")).hexdigest()[:10]

def save_endpoint(endpoint, ephash, eptext):
    os.makedirs("downloads", exist_ok=True)
    jsmd = {}
    if os.path.exists("jsmon.json"):
        with open("jsmon.json", "r") as jsm:
            jsmd = json.load(jsm)
    
    jsmd[endpoint] = jsmd.get(endpoint, []) + [ephash]
    
    with open("jsmon.json", "w") as jsm:
        json.dump(jsmd, jsm)
    
    with open(f"downloads/{ephash}", "w") as epw:
        epw.write(eptext)

def get_previous_endpoint_hash(endpoint):
    if not os.path.exists("jsmon.json"):
        return None
    with open("jsmon.json", "r") as jsm:
        jsmd = json.load(jsm)
        return jsmd.get(endpoint, [])[-1] if endpoint in jsmd else None

def get_diff(old, new):
    opt = {"indent_with_tabs": 1, "keep_function_indentation": 0}
    with open(f"downloads/{old}", "r") as f:
        oldlines = f.readlines()
    with open(f"downloads/{new}", "r") as f:
        newlines = f.readlines()
    
    oldbeautified = jsbeautifier.beautify("".join(oldlines), opt).splitlines()
    newbeautified = jsbeautifier.beautify("".join(newlines), opt).splitlines()
    differ = difflib.HtmlDiff()
    return differ.make_file(oldbeautified, newbeautified)

def notify_discord(endpoint, prev, new, diff):
    prevsize = os.stat(f"downloads/{prev}").st_size if prev else 0
    newsize = os.stat(f"downloads/{new}").st_size
    
    content = f"🔔 Endpoint `{endpoint}` has been updated!\nPrevious hash: `{prev}` ({prevsize} bytes)\nNew hash: `{new}` ({newsize} bytes)"
    
    payload = {
        "content": content,
        "username": "JSMon",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/3.png"
    }
    
    files = {"diff.html": ("diff.html", diff, "text/html")}
    requests.post(DISCORD_WEBHOOK, data=payload, files=files)

def main():
    print("JSMon - Web File Monitor (Discord Edition)")
    
    if DISCORD_WEBHOOK == "CHANGEME":
        print("Please set up your Discord webhook URL in the environment variables!")
        exit(1)
    
    os.makedirs("targets", exist_ok=True)
    if not os.path.exists("targets"):
        print("Please create a 'targets' directory with your target URLs!")
        exit(1)
    
    allendpoints = get_endpoint_list('targets')
    
    for ep in allendpoints:
        if not is_valid_endpoint(ep):
            print(f"Invalid endpoint: {ep}")
            continue
            
        prev_hash = get_previous_endpoint_hash(ep)
        try:
            ep_text = get_endpoint(ep)
            ep_hash = get_hash(ep_text)
            
            if ep_hash != prev_hash:
                save_endpoint(ep, ep_hash, ep_text)
                if prev_hash:
                    diff = get_diff(prev_hash, ep_hash)
                    notify_discord(ep, prev_hash, ep_hash, diff)
                else:
                    print(f"New endpoint enrolled: {ep}")
        except Exception as e:
            print(f"Error monitoring {ep}: {str(e)}")

if __name__ == "__main__":
    main()
