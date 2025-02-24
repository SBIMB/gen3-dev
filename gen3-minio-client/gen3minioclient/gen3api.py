from fastapi import FastAPI
import requests
import json

app = FastAPI()

@app.get("/health")
async def root():
    return {"message": "I am healthy!!!"}

# Opening JSON file containing Gen3 credentials
gen3_credentials_file = open('./../gen3-credentials.json')

# returns JSON object as a python dictionary in the form:
# key = {
#   "api_key": "<actual-key>",
#   "key_id": "<a-key-uuid>"
# }

gen3_credentials = json.load(gen3_credentials_file)

# Pass the API key to the Gen3 API using "requests.post" to receive the access token:
access_token = requests.post('https://gen3-dev.core.wits.ac.za/user/credentials/cdis/access_token', json=gen3_credentials, verify=False).json()

# Print the access_token
print(access_token)

# Run the command 'fastapi dev gen3api.py' to start the development server