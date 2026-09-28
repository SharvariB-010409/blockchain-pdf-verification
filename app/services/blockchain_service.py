import hashlib
import json, os, socket
import uuid
from datetime import datetime, timezone
from app.services.logger import logger
from pathlib import Path
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORE_FILE_PATH = BASE_DIR / "blockchain_store.json"

# block
class Block:
    def __init__(self, index, data, previous_hash):
        self.index = index
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()
    
    # calculate hash SHA-256
    def calculate_hash(self):
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash
        }
        encoded_data = json.dumps(block_data, sort_keys=True).encode()
        return hashlib.sha256(encoded_data).hexdigest()

# blockchain
class Blockchain:
    chain = []
    FILE_PATH = "blockchain_store.json"
    
    # fetch blockchain from postgresql db after stop and restart the server 
    # it resumes the records from where it stopped
    # it doen not delete the records when we stop and restart the server 
    @classmethod
    def rebuild_from_db(cls, db_session):
        from app.db.models import Document 

        # reset chain
        cls.chain = []
        cls.first_block()

        # fetch all saved documents 
        documents = db_session.query(Document).order_by(Document.created_at.asc()).all()

        for doc in documents:
            document_data = {
                "document_id": str(doc.id),
                "document_hash": str(doc.sha256_hash),
                "document_type": str(doc.document_type),
                "blockchain_status": str(doc.blockchain_status).upper(),
                "blockchain_transaction_id": str(doc.blockchain_transaction_id),
                "schema_version": "1.0"
            }

            previous_block = cls.chain[-1]
            new_block = Block(
                index=len(cls.chain),
                data=document_data,
                previous_hash=previous_block.hash
            )
            cls.chain.append(new_block)
            doc.blockchain_block_number = new_block.index
            
        db_session.commit()
        logger.info(f"Blockchain rebuilt from PostgreSQL ({len(cls.chain)} blocks loaded).")
    
    # load chain 
    @classmethod
    def load_chain(cls):
        if os.path.exists(cls.FILE_PATH):
            try:
                with open(cls.FILE_PATH, "r") as f:
                    blocks_data = json.load(f)
                    cls.chain = []
                    for b in blocks_data:
                        block = Block(
                            index=b["index"],
                            data=b["data"],
                            previous_hash=b["previous_hash"]
                        )
                        block.timestamp = b["timestamp"]
                        block.hash = b["hash"]
                        cls.chain.append(block)
                logger.info(f"Blockchain loaded successfully ({len(cls.chain)} blocks).")
            except Exception as e:
                logger.error(f"Error loading blockchain file: {e}")
                cls.first_block()
        else:
            cls.first_block()
            
    # save chain
    @classmethod
    def save_chain(cls):
        chain_data = [
            {
                "index": b.index,
                "timestamp": b.timestamp,
                "data": b.data,
                "previous_hash": b.previous_hash,
                "hash": b.hash,
            }
            for b in cls.chain
        ]
        with open(cls.FILE_PATH, "w") as f:
            json.dump(chain_data, f, indent=4)
       
    # first block
    @classmethod
    def first_block(cls):
        if not cls.chain:
            first_block = Block(index = 0, data = "First Block", previous_hash = "0")
            cls.chain.append(first_block)
    
    # new block     
    @classmethod
    def get_new_block(cls):
        cls.first_block()
        return cls.chain[-1]
    
    # health check (is faric on ?)
    @classmethod
    def health_check(cls, host="localhost", port=7051, timeout=2):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    # upload document
    @classmethod
    def upload_document(cls, document_id, document_hash, document_type, blockchain_status = "CONFIRMED"):
        
        if not cls.health_check():
            logger.warning("Hyperledger Fabric network is unreachable.")
            return {"integrity": False,
                    "message" : "Hyperledger Fabric network is unreachable."
                    }
        
        cls.first_block()
        
        # transaction 
        tx_id = uuid.uuid4()
        document_id = str(document_id) if document_id else str(uuid.uuid4())
        allowed_statuses = ["PENDING", "SUBMITTED", "CONFIRMED", "FAILED"]
        clean_status = str(blockchain_status).upper()
        if clean_status not in allowed_statuses:
            clean_status = "PENDING"
        # Upload New Document
        document_data = { 
                     "document_id" : str(document_id),
                     "document_hash" : str(document_hash),
                     "document_type" : str(document_type),
                     "blockchain_status": clean_status,
                     "blockchain_transaction_id" : str(tx_id),
                     "schema_version" : "1.0"
                    }
    
        # get previous block
        previous_block = cls.chain[-1]
    
        # create new block
        new_block = Block(index = len(cls.chain), data = document_data, previous_hash = previous_block.hash)
    
        # add new block to the chain
        cls.chain.append(new_block)
    
        return({"success" : True,
                "message" : "Document uploaded successfully to the blockchain.",
                "document_id" : document_data.get('document_id'),
                "sha256_hash" : document_data.get('document_hash'),
                "blockchain_status" : document_data.get('blockchain_status'),
                "blockchain_transaction_id" : document_data.get('blockchain_transaction_id'),
                "blockchain_block_number": new_block.index
                })
    
    # verify document
    @classmethod
    def verify_document(cls, document_id: str, document_hash: str):
        cls.first_block()

        target_block = None
        for block in cls.chain:
            if isinstance(block.data, dict) and block.data.get("document_id") == str(document_id):
                target_block = block
                break

        if not target_block:
            return {
                    "blockchain_record_exists": False,
                    "hash_matches": False,
                    "blockchain_status": "FAILED",
                }

        stored_hash = str(target_block.data.get("document_hash", ""))

        case_stored_hash = stored_hash.replace("sha256:", "").lower().strip()
        case_input_hash = str(document_hash).replace("sha256:", "").lower().strip()
        
        chain_hash_matches = case_stored_hash == case_input_hash

        blockchain_status = (
                        str(target_block.data.get("blockchain_status", "CONFIRMED")).strip().upper()
                        )

        return {
                "blockchain_record_exists": True,
                "hash_matches": chain_hash_matches, 
                "blockchain_status": blockchain_status,
                "blockchain_transaction_id": target_block.data.get("blockchain_transaction_id"),
            }
    
    #remove document 
    @classmethod
    def remove_document(cls, document_id: str, db: Session = None):
        from app.db.models import Document
        cls.chain = [
            block for block in cls.chain
            if not (isinstance(block.data, dict) and block.data.get("document_id") == str(document_id))
        ]
        # re index remaining block in fabric after deleting document/s from blockchain
        for i in range(1, len(cls.chain)):
            cls.chain[i].index = i
            cls.chain[i].previous_hash = cls.chain[i - 1].hash
            cls.chain[i].hash = cls.chain[i].calculate_hash()
            
            if db and isinstance(cls.chain[i].data, dict):
                doc_id = cls.chain[i].data.get("document_id")
                if doc_id :
                        doc_record = db.query(Document).filter(Document.id == doc_id).one_or_none()
                        if doc_record:
                            doc_record.blockchain_block_number = i

        if db:
            db.commit()
        cls.save_chain()    
                    
    # check blockchain integrity
    @classmethod
    def check_integrity(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            if current_block.hash != current_block.calculate_hash():
                logger.warning(f"Block {current_block.index} has been tampered with.")
                return {"integrity": False,
                        "message" : f"Block {current_block.index} has been tampered with."
                        }
            
            if current_block.previous_hash != previous_block.hash:
                logger.warning(f"Block {current_block.index} is not linked to the previous block.")
                return {"integrity": False,
                        "message" : f"Block {current_block.index} is not linked to the previous block."
                        }
        
        return {"integrity": True,
                "message" : "Blockchain integrity verified. All blocks are valid and linked correctly."
                }
        
document_blockchain = Blockchain()