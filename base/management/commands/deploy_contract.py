# management/commands/deploy_contract.py
from django.core.management.base import BaseCommand
from base.blockchain import blockchain_service

class Command(BaseCommand):
    help = 'Deploy smart contract to blockchain'
    
    def handle(self, *args, **options):
        self.stdout.write('Deploying smart contract...')
        
        # This will automatically deploy the contract if not already deployed
        if blockchain_service.contract_address:
            self.stdout.write(
                self.style.SUCCESS(f'Contract already deployed at: {blockchain_service.contract_address}')
            )
        else:
            self.stdout.write('Contract deployment initiated...')
            # The contract deployment happens automatically in service initialization