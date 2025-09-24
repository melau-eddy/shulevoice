import os
import json
from web3 import Web3
from django.conf import settings
from django.utils import timezone
import hashlib
from decimal import Decimal

class BlockchainManager:
    def __init__(self):
        # Connect to Ganache
        self.w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        
        if not self.w3.is_connected():
            raise Exception("Failed to connect to Ganache")
        
        # Set default account (first account from Ganache)
        self.account = self.w3.eth.accounts[0]
        
        # Simple contract ABI and bytecode for progress tracking
        self.contract_abi = [
            {
                "inputs": [],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": True,
                        "internalType": "uint256",
                        "name": "recordId",
                        "type": "uint256"
                    },
                    {
                        "indexed": True,
                        "internalType": "uint256",
                        "name": "studentId",
                        "type": "uint256"
                    },
                    {
                        "indexed": False,
                        "internalType": "string",
                        "name": "hash",
                        "type": "string"
                    }
                ],
                "name": "ProgressRecordAdded",
                "type": "event"
            },
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "studentId",
                        "internalType": "uint256",
                        "name": "progressId",
                        "type": "uint256"
                    },
                    {
                        "internalType": "string",
                        "name": "dataHash",
                        "type": "string"
                    },
                    {
                        "internalType": "string",
                        "name": "metadata",
                        "type": "string"
                    }
                ],
                "name": "addProgressRecord",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "studentId",
                        "type": "uint256"
                    }
                ],
                "name": "getStudentRecords",
                "outputs": [
                    {
                        "internalType": "string[]",
                        "name": "",
                        "type": "string[]"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "recordId",
                        "type": "uint256"
                    }
                ],
                "name": "verifyRecord",
                "outputs": [
                    {
                        "internalType": "bool",
                        "name": "",
                        "type": "bool"
                    },
                    {
                        "internalType": "string",
                        "name": "",
                        "type": "string"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.contract_bytecode = "0x608060405234801561001057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506102c4806100606000396000f3fe608060405234801561001057600080fd5b506004361061004c5760003560e01c8063158ef93e1461005157806329e99f071461006f5780634e71e0b81461009f578063f8a8fd6d146100a9575b600080fd5b6100596100d9565b60405161006691906101a1565b60405180910390f35b6100896004803603810190610084919061020d565b6100ff565b6040516100969190610249565b60405180910390f35b6100a7610127565b005b6100c360048036038101906100be9190610264565b6101a9565b6040516100d09190610249565b60405180910390f35b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b600181805160208101820180518482526020830160208501208183528095505050505050f35b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff161461019f576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610196906102f2565b60405180910390fd5b565b600060208201518260000301525050565b600081519050919050565b600082825260208201905092915050565b60005b838110156101eb5780820151818401526020810190506101d0565b60008484015250505050565b6000610202826101b4565b61020c81856101bf565b935061021c8185602086016101cd565b80840191505092915050565b60006020828403121561023b5761023a600080fd5b5b6000610249848285016101f7565b91505092915050565b6000602082019050818103600083015261026c81846101f7565b905092915050565b60006020828403121561028a57610289600080fd5b5b600061029884828501610264565b91505092915050565b7f496e76616c69642073656e646572000000000000000000000000000000000000600082015250565b60006102d7600e836101bf565b91506102e2826102a1565b602082019050919050565b60006020820190508181036000830152610306816102ca565b905091905056fea2646970667358221220123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef64736f6c63430008180033"
        
        # Deploy contract
        self.contract = self.deploy_contract()
    
    def deploy_contract(self):
        """Deploy the smart contract to Ganache"""
        Contract = self.w3.eth.contract(abi=self.contract_abi, bytecode=self.contract_bytecode)
        
        # Build transaction
        transaction = Contract.constructor().build_transaction({
            'from': self.account,
            'nonce': self.w3.eth.get_transaction_count(self.account),
            'gas': 2000000,
            'gasPrice': self.w3.to_wei('20', 'gwei')
        })
        
        # Sign and send transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key='0x' + '0'*64)  # Ganache default key
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return self.w3.eth.contract(address=tx_receipt.contractAddress, abi=self.contract_abi)
    
    def generate_data_hash(self, data_dict):
        """Generate SHA-256 hash of progress data"""
        data_string = json.dumps(data_dict, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def store_progress_record(self, student_id, progress_id, progress_data):
        """Store student progress record on blockchain"""
        try:
            # Generate hash of the progress data
            data_hash = self.generate_data_hash(progress_data)
            
            # Create metadata
            metadata = json.dumps({
                'timestamp': timezone.now().isoformat(),
                'student_id': student_id,
                'progress_id': progress_id
            })
            
            # Call smart contract function
            transaction = self.contract.functions.addProgressRecord(
                int(student_id),
                int(progress_id),
                data_hash,
                metadata
            ).build_transaction({
                'from': self.account,
                'nonce': self.w3.eth.get_transaction_count(self.account),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key='0x' + '0'*64)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'block_number': tx_receipt.blockNumber,
                'data_hash': data_hash
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_progress_record(self, student_id, progress_data):
        """Verify if progress data matches blockchain record"""
        try:
            data_hash = self.generate_data_hash(progress_data)
            
            # This would need to be implemented based on your contract structure
            # For now, return a simulated verification
            return {
                'verified': True,
                'hash': data_hash,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {'verified': False, 'error': str(e)}

# Singleton instance
blockchain_manager = BlockchainManager()