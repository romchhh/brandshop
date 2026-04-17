
import hashlib
import hmac
import time
# from config import secret_key, merchantAccount
import requests

secret_key = 'flk3409refn54t54t*FNJRET'
merchantAccount = 'test_merch_n1'

def test_data():
    dateEnd = 1454364000
    dateBegin = 1454277600
    merchantAccount = "t_me473"
    merchantSignature = "28034760e5d39bfb48780f48c5c51e02ab241b15"
    params = {
        "apiVersion": 1,
        "transactionType": "TRANSACTION_LIST",
        "merchantAccount": merchantAccount,
        "merchantSignature": merchantSignature,
        "dateBegin": dateBegin,
        "dateEnd": dateEnd
    }
    response = requests.post(
        'https://api.wayforpay.com/api',
        json=params,
    )
    print(response)
    print(response.text)


def get_transaction_list():
    dateEnd = int(time.time())
    dateBegin = int(time.time()) - 900000
    into = "{0};{1};{2}".format(merchantAccount, dateBegin, dateEnd)
    merchantSignature = hmac.new(bytearray(secret_key, encoding='utf-8'), bytearray(into, encoding="utf-8"), digestmod=hashlib.md5).hexdigest()

    params = {
        "apiVersion": 1,
        "transactionType": "TRANSACTION_LIST",
        "merchantAccount": merchantAccount,
        "merchantSignature": merchantSignature,
        "dateBegin": dateBegin,
        "dateEnd": dateEnd
    }
    response = requests.post(
        'https://api.wayforpay.com/api',
        json=params,
    )
    return response.json()['transactionList']

print('test: ', get_transaction_list())

def create_invoice(request_name, amount=1.011):
    merchantDomainName = "wayforpay.com/freelance"
    # orderReference = f"myOrder{int(time.time())}"
    orderReference = request_name
    orderDate = int(time.time())
    # amount = 500.01
    currency = "UAH"
    productName = ["Оплата в чат боте"]
    productCount = [1]
    productPrice = [21.1]
    into = "{0};{1};{2};{3};{4};{5};{6};{7};{8}".format(merchantAccount, merchantDomainName,
                                                        orderReference,
                                                        orderDate, amount,
                                                        currency, productName[0],
                                                        productCount[0],
                                                        productPrice[0])
    merchantSignature = hmac.new(bytearray(secret_key, encoding='utf-8'), bytearray(into, encoding="utf-8"), digestmod=hashlib.md5).hexdigest()
    print('merchantSignature: ', merchantSignature)

    params = {
        "transactionType": "CREATE_INVOICE",
        "merchantAccount": merchantAccount,
        "merchantAuthType": "SimpleSignature",
        "merchantDomainName": merchantDomainName,
        "merchantSignature": merchantSignature,
        "apiVersion": 1,
        "language": "ru",
        "orderReference": orderReference,
        "orderDate": orderDate,
        "amount": amount,
        "currency": currency,
        "orderTimeout": 86400,
        "productName": productName,
        "productPrice": [21.1],
        "productCount": productCount,
        "paymentSystems": "applePay;googlePay;privat24;card",
        # "clientFirstName": "Bulba",
        # "clientLastName": "Taras",
        # "clientPhone": "380556667788"
    }

    response = requests.post(
        'https://api.wayforpay.com/api',
        json=params,

    )
    print("------------------")
    print(response)
    print(response.json())
    print(response.json()["invoiceUrl"])
    try:
        invoice_url = response.json()["invoiceUrl"]
    except:
        invoice_url = None
    return invoice_url


def del_invoice(id_payment):
    into = "{0};{1}".format(merchantAccount, id_payment)
    merchantSignature = hmac.new(bytearray(secret_key, encoding='utf-8'), bytearray(into, encoding="utf-8"), digestmod=hashlib.md5).hexdigest()

    params = {
        "apiVersion": "1",
        "transactionType": "REMOVE_INVOICE",
        "merchantAccount": merchantAccount,
        "orderReference": id_payment,
        "merchantSignature": merchantSignature
    }

    response = requests.post(
        'https://api.wayforpay.com/api',
        json=params,

    )
    print(response.text)
