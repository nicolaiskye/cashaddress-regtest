from cashaddress.crypto import *
from cashaddress.base58 import b58decode_check, b58encode_check
import sys


class InvalidAddress(Exception):
    pass


class Address:
    VERSION_MAP = {
        'legacy': [
            ('P2SH', 5, 'mainnet'),
            ('P2PKH', 0, 'mainnet'),
            ('P2SH-TESTNET', 196, 'testnet'),
            ('P2PKH-TESTNET', 111, 'testnet'),
            ('P2SH-REGTEST', 196, 'regtest'),
            ('P2PKH-REGTEST', 111, 'regtest')
        ],
        'cash': [
            ('P2SH', 8, 'mainnet'),
            ('P2PKH', 0, 'mainnet'),
            ('P2SH-TESTNET', 8, 'testnet'),
            ('P2PKH-TESTNET', 0, 'testnet'),
            ('P2SH-REGTEST', 8, 'regtest'),
            ('P2PKH-REGTEST', 0, 'regtest')
        ]
    }
    MAINNET_PREFIX = 'bitcoincash'
    MAINNET_SLP_PREFIX = 'simpleledger'
    TESTNET_PREFIX = 'bchtest'
    TESTNET_SLP_PREFIX = 'slptest'
    REGTEST_PREFIX = 'bchreg'
    REGTEST_SLP_PREFIX = 'slpreg'

    def __init__(self, version, payload, prefix=None):
        self.version = version
        self.payload = payload
        if prefix:
            self.prefix = prefix
        else:
            if Address._address_type('cash', self.version)[2] == "regtest":
                self.prefix = self.REGTEST_PREFIX
            elif Address._address_type('cash', self.version)[2] == "testnet":
                self.prefix = self.TESTNET_PREFIX
            else:
                self.prefix = self.MAINNET_PREFIX

    def __str__(self):
        return 'version: {}\npayload: {}\nprefix: {}'.format(self.version, self.payload, self.prefix)

    def legacy_address(self):
        version_int = Address._address_type('legacy', self.version)[1]
        return b58encode_check(Address.code_list_to_string([version_int] + self.payload))

    def cash_address(self, regtest=False):
        if regtest:
            self.prefix = Address.REGTEST_PREFIX 
        version_int = Address._address_type('cash', self.version)[1]
        payload = [version_int] + self.payload
        payload = convertbits(payload, 8, 5)
        checksum = calculate_checksum(self.prefix, payload)
        return self.prefix + ':' + b32encode(payload + checksum)

    def slp_cash_address(self, regtest=False):
        if regtest:
            self.prefix = Address.REGTEST_SLP_PREFIX
        elif self.prefix == Address.REGTEST_PREFIX:
            self.prefix = Address.REGTEST_SLP_PREFIX
        elif self.prefix == Address.MAINNET_PREFIX:
            self.prefix = Address.MAINNET_SLP_PREFIX
        elif self.prefix == Address.TESTNET_PREFIX:
            self.prefix = Address.TESTNET_SLP_PREFIX
        version_int = Address._address_type('cash', self.version)[1]
        payload = [version_int] + self.payload
        payload = convertbits(payload, 8, 5)
        checksum = calculate_checksum(self.prefix, payload)
        return self.prefix + ':' + b32encode(payload + checksum)

    @staticmethod
    def code_list_to_string(code_list):
        if sys.version_info > (3, 0):
            output = bytes()
            for code in code_list:
                output += bytes([code])
        else:
            output = ''
            for code in code_list:
                output += chr(code)
        return output

    @staticmethod
    def _address_type(address_type, version):
        for mapping in Address.VERSION_MAP[address_type]:
            if mapping[0] == version or mapping[1] == version:
                return mapping
        raise InvalidAddress('Could not determine address version')

    @staticmethod
    def from_string(address_string):
        try:
            address_string = str(address_string)
        except Exception:
            raise InvalidAddress('Expected string as input')
        if ':' not in address_string:
            return Address._legacy_string(address_string)
        else:
            return Address._cash_string(address_string)

    @staticmethod
    def _legacy_string(address_string):
        try:
            decoded = bytearray(b58decode_check(address_string))
        except ValueError:
            raise InvalidAddress('Could not decode legacy address')
        version = Address._address_type('legacy', decoded[0])[0]
        payload = list()
        for letter in decoded[1:]:
            payload.append(letter)
        return Address(version, payload)

    @staticmethod
    def _cash_string(address_string):
        if address_string.upper() != address_string and address_string.lower() != address_string:
            raise InvalidAddress('Cash address contains uppercase and lowercase characters')
        address_string = address_string.lower()
        colon_count = address_string.count(':')
        if colon_count == 0:
            address_string = Address.MAINNET_PREFIX + ':' + address_string
        elif colon_count > 1:
            raise InvalidAddress('Cash address contains more than one colon character')
        prefix, base32string = address_string.split(':')
        decoded = b32decode(base32string)
        if not verify_checksum(prefix, decoded):
            raise InvalidAddress('Bad cash address checksum')
        converted = convertbits(decoded, 5, 8)
        version = Address._address_type('cash', converted[0])[0]
        if prefix == Address.REGTEST_PREFIX:
            version += '-REGTEST'
        elif prefix == Address.TESTNET_PREFIX:
            version += '-TESTNET'
        payload = converted[1:-6]
        return Address(version, payload, prefix)


def to_cash_address(address, regtest=False):
    return Address.from_string(address).cash_address(regtest)

def to_slp_address(address):
    return Address.from_string(address).slp_cash_address()

def to_legacy_address(address):
    return Address.from_string(address).legacy_address()


def is_valid(address):
    try:
        Address.from_string(address)
        return True
    except InvalidAddress:
        return False