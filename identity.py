#!/usr/bin/env python3

# Quick and dirty code, sorry.
# It expects web3 rpc server on localhost:8545 and will use 0-th account to perform transactions

import argparse

import os

from web3 import HTTPProvider
from web3 import Web3

from contracts import ServiceContract, ProductContract, ItemContract

__author__ = 'Xomak'
SERVICE_CONTRACT = "0xF837DB53ac19ce99203931170a822F1b178a5342"

parser = argparse.ArgumentParser(description='Performs some operations, using geth RPC. Please, ensure, '
                                             'that your geth is listeining on http://127.0.0.1:8545/')
parser.add_argument('--setprice', help='New price for service', dest='price', type=float)
parser.add_argument('--register', help='Product to register', dest='product_to_register', nargs=2, metavar='p')
parser.add_argument('--create', help='Product to create', dest='product_to_create', nargs=2, metavar='p')
parser.add_argument('--items', help='Product to browse', dest='product_to_browse', metavar='p')
parser.add_argument('--data', help='Item to browse', dest='item_data', metavar='p')
parser.add_argument('--prop', help='Product to change property', dest='property_change', nargs=2, metavar='p')
parser.add_argument('--owner', help='Product to change owner', dest='owner_change', nargs=2, metavar='p')
parser.add_argument('--writeoff', help='Product to writeoff', dest='writeoff_item', metavar='p')

args = parser.parse_args()

web3 = Web3(HTTPProvider('http://localhost:8545', request_kwargs={'timeout': 60}))
sender_address = web3.eth.accounts[0]
service_contract = ServiceContract(web3, sender_address).at(SERVICE_CONTRACT)

def input_to_contract(input):
    return "0x{}".format(input)

if args.price is not None:
    wei_price = Web3.toWei(args.price, 'ether')
    print("Please, wait...")
    result = service_contract.set_price(wei_price)
    if result:
        print("Price was successfully changed.")

elif args.product_to_register is not None:
    wei_price = Web3.toWei(float(args.product_to_register[1]), 'ether')
    product_name = args.product_to_register[0]
    print("Please, wait...")
    result = service_contract.register_product(product_name, wei_price)
    if result:
        print("Product was successfully registered. Address: {}".format(result))
        with open(os.path.join('products', "{}.ini".format(product_name)), "w") as f:
            f.write("SCADDR={}".format(result[2:]))

elif args.product_to_create is not None:
    qty = int(args.product_to_create[1])
    product_name = args.product_to_create[0]
    contract_address = service_contract.get_address_for(product_name)
    if int(contract_address, 16) != 0:
        print("Product found in registry.")
        product_contract = ProductContract(web3, sender_address).at(contract_address)
        print("Please, wait...")
        result = product_contract.new_items(qty)
        if result:
            for item in result:
                print(item[2:])
    else:
        print("Product is not registered.")

elif args.product_to_browse is not None:
    product_name = args.product_to_browse
    contract_address = service_contract.get_address_for(product_name)
    if int(contract_address, 16) != 0:
        print("Product found in registry.")
        product_contract = ProductContract(web3, sender_address).at(contract_address)
        for e in product_contract.get_items():
            print(e[2:])

elif args.item_data is not None:
    item_contract_address = input_to_contract(args.item_data)
    item_contract = ItemContract(web3, sender_address).at(item_contract_address)
    product_contract_address = item_contract.get_product_address()
    product_contract = ProductContract(web3, sender_address).at(product_contract_address)
    service_address = product_contract.get_service_address()
    if service_address == SERVICE_CONTRACT:
        print("Validity confirmed.")
    else:
        print("Warning! This item is not connected with the current service.")

    if not item_contract.is_destroyed():
        print("Owner: {}".format(item_contract.get_owner()))
        print("Properties: {}".format(item_contract.get_properties()))
    else:
        print("Item was destroyed.")

elif args.property_change is not None:
    item_contract_address = input_to_contract(args.property_change[1])
    new_property = args.property_change[0]
    item_contract = ItemContract(web3, sender_address).at(item_contract_address)
    print("Please, wait...")
    item_contract.set_properties(new_property)
    print("Property was successfully changed.")

elif args.owner_change is not None:
    item_contract_address = input_to_contract(args.owner_change[1])
    new_owner = args.owner_change[0]
    item_contract = ItemContract(web3, sender_address).at(item_contract_address)
    print("Please, wait...")
    item_contract.set_owner(new_owner)
    print("Owner was successfully changed.")

elif args.writeoff_item is not None:
    item_contract_address = input_to_contract(args.writeoff_item)
    item_contract = ItemContract(web3, sender_address).at(item_contract_address)
    owner_address = item_contract.get_owner_address()
    destroy_pending = item_contract.is_destroy_pending()
    is_destroyed = item_contract.is_destroyed()

    is_owner = owner_address.lower() == sender_address.lower()

    if is_destroyed:
        print("Item was already destroyed.")
    elif destroy_pending:
        print("Destroying item. Please, wait...")
        if item_contract.confirm_destroy():
            print("Item was destroyed")
    elif is_owner:
        print("Issuing destroy request...")
        if item_contract.request_destroy():
            print("Request was issued")
    else:
        print("You can not issue destroy request.")
