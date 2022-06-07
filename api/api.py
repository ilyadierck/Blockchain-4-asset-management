from flask import Flask, request, abort
from flask_cors import CORS
from flask_restful import Resource, Api, reqparse
import json
from pinatapy import PinataPy
import requests
from web3 import Web3
import uuid
from hexbytes import HexBytes

# CONFIG VARIABLES
gateway = "https://gateway.pinata.cloud/ipfs/"
CONTRACT_ADDRESS = "0xaFAe0a3Cb5e02EEcbf0cfa4B7FABfC7e1566dA8f"
ABI = [
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "id",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ipfsUrl",
				"type": "string"
			}
		],
		"name": "addAsset",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "oldId",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "oldIpfsUrl",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "newIpfsUrl",
				"type": "string"
			}
		],
		"name": "editAsset",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "id",
				"type": "string"
			}
		],
		"name": "getAsset",
		"outputs": [
			{
				"components": [
					{
						"internalType": "string",
						"name": "ipfsUrl",
						"type": "string"
					},
					{
						"internalType": "string[]",
						"name": "pastVersions",
						"type": "string[]"
					}
				],
				"internalType": "struct Asset",
				"name": "",
				"type": "tuple"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]
assetManager = None
FUNDS_ACCOUNT = "0x9708938C7ae905C306b75FA628bC433048D8323f"

# API INIT
app = Flask(__name__)
CORS(app)
api = Api(app)

# PINATA IPFS INIT
pinata_api_key = "bad029a18af4985d36f8"
pinata_secret_api_key = str(
    "a7b4a359214660180ff24750b7c822ae328bdfb99ae468302d6c2b9fc7f9a8cb")
pinata = PinataPy(pinata_api_key, pinata_secret_api_key)


w3 = Web3(Web3.HTTPProvider("https://volta-rpc.energyweb.org"))
if w3.isConnected():
    assetManager = w3.eth.contract(
        address=CONTRACT_ADDRESS,
        abi=ABI)
else:
    print("Error in connecting to the volta blockchain")


def calculateIdAsset():
    return str(uuid.uuid4())


def getAssetData(id):
    if (type(id) == dict):
        return id
    blockchainRecord = assetManager.functions.getAsset(str(id)).call()
    if blockchainRecord[0] == "":
        abort(404)
    ipfsUrl = blockchainRecord[0]
    pastVersions = blockchainRecord[1]
    assetData = requests.get(url=gateway+ipfsUrl).json()
    assetData["pastVersions"] = []
    assetData["ipfsUrl"] = ipfsUrl
    for pastVersion in pastVersions:
        if (pastVersion != ""):
            assetData["pastVersions"].append(
                requests.get(url=gateway+pastVersion).json())

    newChilderen = []
    for child in assetData["childeren"]:
        newChilderen.append(getAssetData(child))
    assetData["childeren"] = newChilderen
    return assetData


def addAssetToBlockchain(id, ipfsUrl):
    nonce = w3.eth.get_transaction_count(FUNDS_ACCOUNT)
    transaction_hash = assetManager.functions.addAsset(id, ipfsUrl).buildTransaction({
        'nonce': nonce,
    })
    signed_txn = w3.eth.account.sign_transaction(
        transaction_hash, private_key="REDACTED")
    transaction = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(transaction)


def editAssetOnBlockchain(oldId, oldIpfsUrl, newIpfsUrl):
    nonce = w3.eth.get_transaction_count(FUNDS_ACCOUNT)
    transaction_hash = assetManager.functions.editAsset(oldId, oldIpfsUrl, newIpfsUrl).buildTransaction({
        'nonce': nonce,
    })
    signed_txn = w3.eth.account.sign_transaction(
        transaction_hash, private_key="REDACTED")
    transaction = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(transaction)


class assetLookup(Resource):
    def get(self, id):
        return getAssetData(id)

    def patch(self, id):
        newAssetData = request.json
        newAssetData = json.loads(json.dumps(newAssetData))
        oldAssetData = getAssetData(id)
        newIpfsUrl = pinata.pin_json_to_ipfs(newAssetData)["IpfsHash"]
        editAssetOnBlockchain(
            oldAssetData["id"], oldAssetData["ipfsUrl"], newIpfsUrl)
        print("Edited asset id: " + oldAssetData["id"])
        return newAssetData



def addChildToAssetParent(parentAssetData, childId):
    parentAssetData["childeren"].append(childId)
    newIpfsUrl = pinata.pin_json_to_ipfs(parentAssetData)["IpfsHash"]
    editAssetOnBlockchain(parentAssetData["id"], parentAssetData["ipfsUrl"], newIpfsUrl)
    print("added child to parent id: " + parentAssetData["id"])

class assets(Resource):
    def post(self):
        assetData = request.json
        assetData = json.loads(json.dumps(assetData))
        id = calculateIdAsset()
        assetData["id"] = id
        parentId = assetData["parent"]
        if parentId != "":
            addChildToAssetParent(getAssetData(parentId), id)
        ipfsUrl = pinata.pin_json_to_ipfs(assetData)["IpfsHash"]
        addAssetToBlockchain(id, ipfsUrl)
        print("Added id: " + id)

        return assetData


api.add_resource(assets, '/assets')
api.add_resource(assetLookup, '/assets/<string:id>')

if __name__ == '__main__':
    app.run(debug=True)  # run our Flask app
