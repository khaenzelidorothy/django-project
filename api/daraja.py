import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
import base64
import datetime

class DarajaAPI:
    def __init__(self):
        self.consumer_key = settings.DARAJA_CONSUMER_KEY
        self.consumer_secret = settings.DARAJA_CONSUMER_SECRET
        self.business_shortcode = settings.DARAJA_SHORTCODE
        self.passkey = settings.DARAJA_PASSKEY
        self.base_url = "https://sandbox.safaricom.co.ke"
        self.callback_url = settings.DARAJA_CALLBACK_URL

    def get_access_token(self):
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret),
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise Exception(f"Failed to get access token: {data}")
        return token

    def stk_push(self, buyer_phone, amount, transaction_id, transaction_desc):
        access_token = self.get_access_token()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        data_to_encode = f"{self.business_shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(data_to_encode.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),
            "PartyA": buyer_phone,
            "PartyB": self.business_shortcode,
            "PhoneNumber": buyer_phone,
            "CallBackURL": self.callback_url,
            "AccountReference": transaction_id,
            "TransactionDesc": transaction_desc,
        }
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        response = requests.post(url, headers=headers, json=payload)
        print("Daraja raw response:", response.text)
        response.raise_for_status()
        return response.json()



    










    def b2c_payment(self, artisan_phone, amount, transaction_id, transaction_desc, occassion=""):
        access_token = self.get_access_token()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        data_to_encode = f"{self.business_shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(data_to_encode.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "InitiatorName": settings.DARAJA_INITIATOR_NAME,    
            "SecurityCredential": settings.DARAJA_SECURITY_CREDENTIAL, 
            "CommandID": "BusinessPayment",
            "Amount": str(int(amount)),
            "PartyA": self.business_shortcode,
            "PartyB": artisan_phone,
            "Remarks": transaction_desc,
            "QueueTimeOutURL": settings.DARAJA_B2C_TIMEOUT_URL,  
            "ResultURL": settings.DARAJA_B2C_RESULT_URL,        
            "Occasion": occassion,
        }
        url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
        response = requests.post(url, headers=headers, json=payload)
        print("Daraja B2C raw response:", response.text)
        response.raise_for_status()
        return response.json()




















    