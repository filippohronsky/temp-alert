import azure.functions as func
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError
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
    
    last_temperature = read_temperature_from_blob()
    temperature_change = round(temperature - last_temperature,2)
    write_temperature_to_blob(temperature)
    
        # Druhá správa s porovnaním teploty
    if abs(temperature_change) >= 1:
        change_direction = "zvýšila" if temperature_change > 0 else "znížila"
        change_message = f"📛 Teplota sa {change_direction} o **{abs(temperature_change)}** °C oproti poslednému meraniu."
        send_message_to_webex(change_message)

    # Vytvorenie správy
    message = f"ℹ️ **Teplota:** {temperature} **, Vlhkosť:** {humidity} **, CO2:** {co2} **, IAQ:** {iaq} **, Tlak:** {pressure} **, Napätie batérie:** {battery_v}"
    
    # Odoslanie správy do Webex
    send_message_to_webex(message)

def send_message_to_webex(message):
    webex_token = os.environ.get("WEBEX_TEAMS_ACCESS_TOKEN")
    room_id = os.environ.get("WEBEX_ROOM_ID")
    
    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {webex_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "roomId": room_id,
        "markdown": message
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        logging.info("Správa bola úspešne odoslaná do Webex Teams.")
    else:
        logging.error(f"Chyba pri odosielaní správy: {response.text}")
        

def write_temperature_to_blob(temperature):
    connect_str = os.getenv('AzureWebJobsStorage')
    container_name = 'container-data'
    blob_name = 'last_temperature.txt'
    
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    blob_client.upload_blob(str(temperature), overwrite=True)

def read_temperature_from_blob():
    connect_str = os.getenv('AzureWebJobsStorage')
    container_name = 'container-data'
    blob_name = 'last_temperature.txt'
    
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    try:
        # Pokus o stiahnutie obsahu blobu
        stream = blob_client.download_blob()
        last_temperature = float(stream.readall())
    except ResourceNotFoundError:
        # Ak blob neexistuje, vráť predvolenú hodnotu teploty
        last_temperature = 0.0

    return last_temperature
