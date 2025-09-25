# management/commands/setup_blockchain.py
from django.core.management.base import BaseCommand
from base.blockchain import blockchain_service
from contracts.compile import compile_contract_simple
import os

class Command(BaseCommand):
    help = 'Setup and test blockchain connection'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--private-key',
            type=str,
            help='Private key for blockchain account'
        )
        parser.add_argument(
            '--compile',
            action='store_true',
            help='Compile smart contract'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Setting up blockchain integration...')
        
        # Compile contract if requested
        if options['compile']:
            self.stdout.write('Compiling smart contract...')
            result = compile_contract()
            if result:
                self.stdout.write(
                    self.style.SUCCESS('Smart contract compiled successfully!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to compile smart contract')
                )
                return
        
        # Test connection
        network_info = blockchain_service.get_network_info()
        
        if network_info['connected']:
            self.stdout.write(
                self.style.SUCCESS(f"Connected to blockchain network (ID: {network_info['network_id']})")
            )
            self.stdout.write(f"Latest block: {network_info['latest_block']}")
            
            if network_info['owner_address']:
                self.stdout.write(f"Owner address: {network_info['owner_address']}")
                self.stdout.write(f"Balance: {network_info['balance']} wei")
            
            if network_info['contract_address']:
                self.stdout.write(f"Contract address: {network_info['contract_address']}")
            else:
                self.stdout.write("No contract deployed yet")
        else:
            self.stdout.write(
                self.style.ERROR("Failed to connect to blockchain network")
            )
            self.stdout.write("Make sure Ganache is running on http://localhost:7545")