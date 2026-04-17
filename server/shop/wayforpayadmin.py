import hashlib
import hmac
import time
# from config import secret_key, merchantAccount
import requests
import os

#secret_key = 'flk3409refn54t54t*FNJRET'
#merchantAccount = 'test_merch_n1'

secret_key = os.getenv('PAY_SECRET_KEY')
merchantAccount = os.getenv('PAY_MERCHANT_ID')

api_host = os.getenv('API_HOST')
serviceUrl = f'{api_host}/api/wayforpay_hook'

class WayForPayAdmin:
    @classmethod
    def create_invoice(cls, request_name, amount=1.011):
        if float(amount) <=0:
            return None
        print(amount)
        merchantDomainName = "wayforpay.com/freelance"
        orderReference = request_name
        orderDate = int(time.time())
        currency = "UAH"
        productName = ["Товари"]
        productCount = [1]
        productPrice = [amount]
        into = "{0};{1};{2};{3};{4};{5};{6};{7};{8}".format(merchantAccount, merchantDomainName,
                                                            orderReference,
                                                            orderDate, amount,
                                                            currency, productName[0],
                                                            productCount[0],
                                                            productPrice[0])
        merchantSignature = hmac.new(bytearray(secret_key, encoding='utf-8'), bytearray(into, encoding="utf-8"),
                                     digestmod=hashlib.md5).hexdigest()
        print('merchantSignature: ', merchantSignature)

        params = {
            "transactionType": "CREATE_INVOICE",
            "merchantAccount": merchantAccount,
            "merchantAuthType": "SimpleSignature",
            "merchantDomainName": merchantDomainName,
            "merchantSignature": merchantSignature,
            "apiVersion": 1,
            "language": "ua",
            "orderReference": orderReference,
            "orderDate": orderDate,
            "amount": amount,
            "currency": currency,
            "orderTimeout": 86400,
            "productName": productName,
            "productPrice": productPrice,
            "productCount": productCount,
            "paymentSystems": "applePay;googlePay;privat24;card",
            "serviceUrl": serviceUrl
        }

        response = requests.post(
            'https://api.wayforpay.com/api',
            json=params,
        )

        print(response.json())
        try:
            invoice_url = response.json()["invoiceUrl"]
        except:
            invoice_url = None
        return invoice_url

# WayForPayAdmin.create_invoice('10010011')
