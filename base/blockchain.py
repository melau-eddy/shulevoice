# base/blockchain/service.py
import json
import hashlib
from web3 import Web3
import os
import time
from django.conf import settings

class RealBlockchainService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.GANACHE_URL))
        self.contract_address = None
        self.contract = None
        self.owner_account = None
        
        self.initialize_contract()
    
    def initialize_contract(self):
        """Initialize or deploy the smart contract"""
        if hasattr(settings, 'CONTRACT_OWNER_PRIVATE_KEY') and settings.CONTRACT_OWNER_PRIVATE_KEY:
            try:
                self.owner_account = self.w3.eth.account.from_key(settings.CONTRACT_OWNER_PRIVATE_KEY)
            except Exception as e:
                print(f"Error initializing account: {e}")
                self.owner_account = None
        
        # Try to load contract if address exists
        contract_address = getattr(settings, 'CONTRACT_ADDRESS', None)
        if contract_address and self.w3.is_address(contract_address):
            self.contract_address = contract_address
            # Load ABI and create contract instance
            abi = self.load_contract_abi()
            if abi:
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=abi
                )
    
    def load_contract_abi(self):
        """Load contract ABI from file"""
        try:
            contract_path = os.path.join(os.path.dirname(__file__), 'contracts', 'EduTrack.json')
            if os.path.exists(contract_path):
                with open(contract_path, 'r') as f:
                    contract_data = json.load(f)
                    return contract_data.get('abi')
        except Exception as e:
            print(f"Error loading contract ABI: {e}")
        return None
    
    def deploy_contract(self, abi, bytecode):
        """Deploy the smart contract to blockchain"""
        if not self.owner_account:
            raise Exception("Contract owner private key not configured")
        
        try:
            # Prepare contract deployment
            contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Build transaction
            transaction = contract.constructor().build_transaction({
                'from': self.owner_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.owner_account.address),
                'gas': getattr(settings, 'GAS_LIMIT', 3000000),
                'gasPrice': self.w3.to_wei(getattr(settings, 'GAS_PRICE', 20), 'gwei')
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.CONTRACT_OWNER_PRIVATE_KEY
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            self.contract_address = receipt.contractAddress
            
            if abi:
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=abi
                )
            
            print(f"Contract deployed at: {self.contract_address}")
            return self.contract_address
            
        except Exception as e:
            print(f"Error deploying contract: {e}")
            raise
    
    def record_student_progress(self, student_id, progress_data):
        """Record student progress on real blockchain"""
        try:
            # Create data hash for integrity
            data_hash = self.calculate_data_hash(progress_data)
            
            if self.contract:
                # Use smart contract
                transaction = self.contract.functions.recordProgress(
                    student_id,
                    data_hash,
                    int(time.time()),
                    json.dumps(progress_data)
                ).build_transaction({
                    'from': self.owner_account.address,
                    'nonce': self.w3.eth.get_transaction_count(self.owner_account.address),
                    'gas': getattr(settings, 'GAS_LIMIT', 3000000),
                    'gasPrice': self.w3.to_wei(getattr(settings, 'GAS_PRICE', 20), 'gwei')
                })
                
                signed_txn = self.w3.eth.account.sign_transaction(
                    transaction, 
                    private_key=settings.CONTRACT_OWNER_PRIVATE_KEY
                )
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                return {
                    'success': True,
                    'transaction_hash': tx_hash.hex(),
                    'block_number': receipt.blockNumber,
                    'gas_used': receipt.gasUsed,
                    'contract_used': True
                }
            else:
                # Fallback to direct transaction
                return self.send_direct_transaction(
                    student_id, 
                    'progress_update', 
                    data_hash, 
                    progress_data
                )
                
        except Exception as e:
            print(f"Blockchain error: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_direct_transaction(self, student_id, action_type, data_hash, metadata):
        """Send direct transaction when contract is not available"""
        if not self.owner_account:
            return {'success': False, 'error': 'No blockchain account configured'}
        
        try:
            transaction = {
                'to': self.owner_account.address,
                'value': 0,
                'gas': getattr(settings, 'GAS_LIMIT', 3000000),
                'gasPrice': self.w3.to_wei(getattr(settings, 'GAS_PRICE', 20), 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.owner_account.address),
                'data': self.w3.to_hex(text=json.dumps({
                    'student_id': student_id,
                    'action_type': action_type,
                    'data_hash': data_hash,
                    'metadata': metadata,
                    'timestamp': int(time.time())
                }))
            }
            
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.CONTRACT_OWNER_PRIVATE_KEY
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'transaction_hash': tx_hash.hex(),
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
                'contract_used': False
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_progress(self, student_id, original_data):
        """Verify progress data integrity on blockchain"""
        try:
            data_hash = self.calculate_data_hash(original_data)
            
            if self.contract:
                # Query smart contract
                result = self.contract.functions.verifyProgress(
                    student_id, 
                    data_hash
                ).call()
                return result
            else:
                # Search transactions for matching data
                return self.search_transactions(student_id, data_hash)
                
        except Exception as e:
            print(f"Verification error: {e}")
            return False
    
    def search_transactions(self, student_id, data_hash):
        """Search blockchain transactions for matching data"""
        try:
            latest_block = self.w3.eth.block_number
            search_range = min(1000, latest_block)
            
            for block_num in range(latest_block, max(0, latest_block - search_range), -1):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    for tx in block.transactions:
                        if tx.get('to') and tx['to'].lower() == self.owner_account.address.lower():
                            if tx.get('input'):
                                try:
                                    tx_data = json.loads(self.w3.to_text(tx['input']))
                                    if (tx_data.get('student_id') == student_id and 
                                        tx_data.get('data_hash') == data_hash):
                                        return True
                                except:
                                    continue
                except:
                    continue
            
            return False
        except Exception as e:
            print(f"Search error: {e}")
            return False
    
    def calculate_data_hash(self, data):
        """Calculate SHA-256 hash of data"""
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def get_network_info(self):
        """Get blockchain network information"""
        try:
            is_connected = self.w3.is_connected()
            network_id = self.w3.eth.chain_id if is_connected else None
            latest_block = self.w3.eth.block_number if is_connected else None
            balance = self.w3.eth.get_balance(self.owner_account.address) if self.owner_account and is_connected else 0
            
            return {
                'connected': is_connected,
                'network_id': network_id,
                'latest_block': latest_block,
                'owner_address': self.owner_account.address if self.owner_account else None,
                'contract_address': self.contract_address,
                'balance': balance
            }
        except Exception as e:
            print(f"Network info error: {e}")
            return {
                'connected': False,
                'network_id': None,
                'latest_block': None,
                'owner_address': None,
                'contract_address': None,
                'balance': 0
            }

# Singleton instance
blockchain_service = RealBlockchainService()