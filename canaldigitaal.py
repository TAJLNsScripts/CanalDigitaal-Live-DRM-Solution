import requests
import json
from bs4 import BeautifulSoup
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH

#Config
#Find the token in DevTools -> Application -> Local Storage -> token
token = ""
WVD_PATH = "./WVD.wvd"

def do_cdm(pssh, licenseUrl):
    pssh = PSSH(pssh)
    
    device = Device.load(WVD_PATH)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()

    challenge = cdm.get_license_challenge(session_id, pssh)

    licence = requests.post(licenseUrl, data=challenge)
    licence.raise_for_status()

    cdm.parse_license(session_id, licence.content)

    for key in cdm.get_keys(session_id):
        if key.type != 'SIGNING':
            print(f" - {key.kid.hex}:{key.key.hex()}")

    cdm.close(session_id)

def get_initial(token, channel_id):
    headers = {
        'authority': 'tvapi.solocoo.tv',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer ' + token,
        'content-type': 'application/json',
    }

    json_data = {
        'player': {
            'name': 'RxPlayer',
            'version': '3.29.0',
            'capabilities': {
                'mediaTypes': [
                    'DASH',
                ],
                'drmSystems': [
                    'Widevine',
                ],
                'smartLib': True,
            },
        },
    }

    response = requests.post('https://tvapi.solocoo.tv/v1/assets/' + channel_id + '/play', headers=headers, json=json_data)

    data = response.json()

    try:
        return data['url'], data['drm']['licenseUrl']
    except:
        print('Failed to get temp mpd')
        print(response.content)
        quit()

def get_mpd(temp_mpd):
    response = requests.get(temp_mpd + '&response=200&bk-ml=1')
    
    try:
        return response.headers['Location']
    except:
        print('Failed to get mpd')
        print(response.headers)
        quit()

def extract_pssh(mpd_url):
    try:
        response = requests.get(mpd_url)
        
        psshs = []
        for p in BeautifulSoup(response.content, features="xml").findAll('cenc:pssh'):
            psshs.append(p.text)
        
        return min(psshs, key=len)
    except Exception as e:
        print('Failed to extract pssh from manifest')
        print(e)
        quit()
    


canal_url = input('Enter Canal Digitaal url: ')
channel_id = canal_url.split('/')[-1].split('?')[0]
if channel_id is None:
    print('Error processing Canal Digitaal url')
    quit()

temp_mpd, license_url = get_initial(token, channel_id)

if 'index.mpd' in temp_mpd:
    mpd_url = get_mpd(temp_mpd)
else:
    mpd_url = temp_mpd

pssh = extract_pssh(mpd_url)

print('URL: ' + mpd_url)
print('Keys:')

do_cdm(pssh, license_url)