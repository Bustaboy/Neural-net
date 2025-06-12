# blockchain/audit_chain.py
import hashlib
import json
from typing import List, Dict

class AuditBlockchain:
    """Immutable audit trail using blockchain technology"""
    
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
        
    def create_genesis_block(self):
        """Create the first block"""
        genesis_block = {
            'index': 0,
            'timestamp': str(datetime.utcnow()),
            'transactions': [],
            'previous_hash': '0',
            'nonce': 0
        }
        genesis_block['hash'] = self.calculate_hash(genesis_block)
        self.chain.append(genesis_block)
    
    def add_transaction(self, transaction: Dict):
        """Add trading decision to blockchain"""
        transaction['timestamp'] = str(datetime.utcnow())
        transaction['hash'] = self.calculate_transaction_hash(transaction)
        self.pending_transactions.append(transaction)
        
    def mine_block(self, difficulty: int = 4):
        """Mine a new block with proof of work"""
        if not self.pending_transactions:
            return False
            
        new_block = {
            'index': len(self.chain),
            'timestamp': str(datetime.utcnow()),
            'transactions': self.pending_transactions,
            'previous_hash': self.chain[-1]['hash'],
            'nonce': 0
        }
        
        # Proof of work
        while not self.validate_proof(new_block, difficulty):
            new_block['nonce'] += 1
            
        new_block['hash'] = self.calculate_hash(new_block)
        self.chain.append(new_block)
        self.pending_transactions = []
        
        return new_block
