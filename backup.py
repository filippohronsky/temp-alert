import azure.functions as func
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import logging
import base64
import json
import requests
import os

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="container-data/{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{min}.json",
                               connection="AzureWebJobsStorage") 
def BlobTrigger(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob "
                f"Name: {myblob.name} "
                f"Blob Size: {myblob.length} bytes")
    
    # Čítanie celého obsahu blobu
    full_blob_content = myblob.read()
    logging.info(f"JSON správa: {full_blob_content}")
    
    
    # Konverzia obsahu blobu z bytes do stringu a parsovanie JSON
    full_data = json.loads(full_blob_content.decode('utf-8'))
    
    # Extrahovanie a dekódovanie hodnoty Body
    encoded_body = full_data['Body']
    decoded_body = base64.b64decode(encoded_body).decode('utf-8')
    
    # Parsovanie dekódovaného JSON obsahu tela
    data = json.loads(decoded_body)
    
    # Získanie údajov z dekódovaného JSON
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    co2 = data.get('co2')
    iaq = data.get('iaq')
    pressure = data.get('pressure')
    battery_v = data.get('battery_v')

    # Vytvorenie správy
    message = f"Teplota: {temperature}, Vlhkosť: {humidity}, CO2: {co2}, IAQ: {iaq}, Tlak: {pressure}, Napätie batérie: {battery_v}"
    
    # Odoslanie správy do Webex
    send_message_to_webex(message)

def send_message_to_webex(message):
    webex_token = os.environ.get("WEBEX_TEAMS_ACCESS_TOKEN")
    room_id = os.environ.get("WEBEX_ROOM_ID")
    logging.info(f"WEBEX hodnoty: {webex_token} a {room_id}")
    
    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {webex_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "roomId": room_id,
        "text": message
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        logging.info("Správa bola úspešne odoslaná do Webex Teams.")
    else:
        logging.error(f"Chyba pri odosielaní správy: {response.text}")
