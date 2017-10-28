import json
from threading import Event

from web3.exceptions import BadFunctionCallOutput

from utils import TransactionException

__author__ = 'Xomak'


class Contract:
    def __init__(self, web3, name, sender_address=None):
        self.web3 = web3
        self.sender_address = sender_address
        if self.sender_address is None:
            raise ValueError("Can not find account to send transaction from.")
        self.contract = None
        self.contract_factory = None
        with open("abi/{}.json".format(name), "r") as f:
            abi = json.loads(f.read())
            self.contract_factory = web3.eth.contract(
                abi=abi,
            )

    def wait_for_transaction(self, transaction):
        feedback_received = Event()

        def callback(block_hash):
            block = self.web3.eth.getBlock(block_hash)
            if transaction in block['transactions']:
                feedback_received.set()

        new_block_filter = self.web3.eth.filter('latest')
        new_block_filter.watch(callback)
        feedback_received.wait()

    def execute_sync(self, contract_func, event):
        transaction_hash = contract_func()
        self.wait_for_transaction(transaction_hash)
        receipt = self.web3.eth.getTransactionReceipt(transaction_hash)
        block_number = receipt['blockNumber']
        if event is not None:
            event_filter = self.contract.pastEvents(event, {'fromBlock': block_number, 'toBlock': 'latest'})
            events = event_filter.get()
            events = [e for e in events if e['transactionHash'] == transaction_hash]
        else:
            events = []
        return {'transactionHash': transaction_hash, 'status': receipt['status'], 'events': events}

    def at(self, address):
        self.contract = self.contract_factory(address)
        return self


class ServiceContract(Contract):

    REGISTER_GAS_LIMIT = 5000000

    def __init__(self, web3, sender_address=None):
        super().__init__(web3, "service", sender_address)

    def set_price(self, new_price):
        result = self.execute_sync(lambda: self.contract.transact(
            {"gas": ServiceContract.REGISTER_GAS_LIMIT, "from": self.sender_address}
        ).setPrice(new_price), None)
        if result['status'] == 1:
            return True
        else:
            raise TransactionException()

    def get_price(self):
        return self.contract.call().price()

    def get_address_for(self, product):
        return self.contract.call().getProductAddress(product)

    def register_product(self, name, value):
        result = self.execute_sync(lambda: self.contract.transact(
            {"gas": ServiceContract.REGISTER_GAS_LIMIT, "value": value, "from": self.sender_address}
        ).registerProduct(name), "ProductRegistered")
        if result['status'] == 1:
            if len(result['events']) == 1:
                return result['events'][0]['args']['contractAddress']
            else:
                raise TransactionException()
        else:
            raise TransactionException()


class ProductContract(Contract):
    NEW_ITEM_GAS_LIMIT = 5000000

    def __init__(self, web3, sender_address=None):
        super().__init__(web3, "product", sender_address)

    def get_service_address(self):
        return self.contract.call().serviceAddress()

    def new_items(self, qty):
        result = self.execute_sync(lambda: self.contract.transact(
            {"gas": ProductContract.NEW_ITEM_GAS_LIMIT, "from": self.sender_address}
        ).newItems(qty), "ItemCreated")
        if result['status'] == 1:
            if len(result['events']) >= 1:
                return [e['args']['itemAddress'] for e in result['events']]
            else:
                raise TransactionException()
        else:
            raise TransactionException()

    def get_items(self):
        addr = "0x0"
        i = 0
        items = []
        while int(addr, 16) != 0 or i == 0:
            try:
                addr = self.contract.call().items(i)
                items.append(addr)
                i += 1
            except BadFunctionCallOutput:
                addr = "0x0"
        return items


class ItemContract(Contract):
    DATA_SET_GAS_LIMIT = 5000000

    def __init__(self, web3, sender_address=None):
        super().__init__(web3, "item", sender_address)

    def get_product_address(self):
        return self.contract.call().productAddress()

    def get_properties(self):
        properties = self.contract.call().getProperties()
        return properties

    def get_owner_address(self):
        return self.contract.call().ownerAddress()

    def get_owner(self):
        owner = self.contract.call().getOwner()
        return owner

    def is_destroy_pending(self):
        return self.contract.call().isDestroyPending()

    def is_destroyed(self):
        return self.contract.call().isDestroyed()

    def set_owner(self, new_owner):
        result = self.execute_sync(lambda: self.contract.transact(
            {"gas": ItemContract.DATA_SET_GAS_LIMIT, "from": self.sender_address}
        ).setOwner(new_owner), None)
        if result['status'] == 1:
            return True
        else:
            raise TransactionException()

    def set_properties(self, new_properties):
        result = self.execute_sync(lambda: self.contract.transact(
            {"gas": ItemContract.DATA_SET_GAS_LIMIT, "from": self.sender_address}
        ).setProperties(new_properties), None)
        if result['status'] == 1:
            return True
        else:
            raise TransactionException()

    def request_destroy(self):
        result = self.execute_sync(lambda: self.contract.transact(
            {"from": self.sender_address}
        ).requestDestroy(), None)
        if result['status'] == 1:
            return True
        else:
            raise TransactionException()

    def confirm_destroy(self):
        result = self.execute_sync(lambda: self.contract.transact(
            {"from": self.sender_address}
        ).confirmDestroy(), None)
        if result['status'] == 1:
            return True
        else:
            raise TransactionException()
