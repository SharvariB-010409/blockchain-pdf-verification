from app.services.logger import logger
import asyncio
from hfc.fabric import Client


class Blockchain:
    @staticmethod
    def upload_document(document_id: str, document_hash: str, document_type: str) -> dict:
        """Connects directly to Fabric peer without needing Node.js."""
        try:
            loop = asyncio.get_event_loop()
            client = Client(net_profile="path/to/connection.json")
            user = client.get_user('org1.example.com', 'Admin')

            # Call your deployed chaincode function
            tx_id = loop.run_until_complete(client.chaincode_invoke(
                requestor=user,
                channel_name='mychannel',
                peers=['peer0.org1.example.com'],
                args=[document_id, document_hash, document_type],
                cc_name='basic',
                fcn='RegisterDocument'
            ))

            return {
                "blockchain_status": "CONFIRMED",
                "blockchain_transaction_id": str(tx_id)
            }
        except Exception as e:
            logger.error(f"Fabric direct connection error: {str(e)}")
            raise