import logging
import motor.motor_asyncio
from pymongo.errors import ServerSelectionTimeoutError, DuplicateKeyError
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all interactions with the MongoDB database."""

    def __init__(self, mongo_uri: str, db_name: str):
        """
        Initializes the MongoDB connection and selects the database.

        Args:
            mongo_uri (str): The connection URI for the MongoDB instance.
            db_name (str): The name of the database to use.
        """
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            self.db = self.client[db_name]
            logger.info(f"Successfully connected to MongoDB database: {db_name}")
        except Exception as e:
            logger.critical(f"Failed to connect to MongoDB: {e}")
            raise

    async def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Finds a single document in a collection.

        Args:
            collection_name (str): The name of the collection to search.
            query (dict): The filter query to find the document.

        Returns:
            Optional[dict]: The found document, or None if not found.
        """
        try:
            collection = self.db[collection_name]
            return await collection.find_one(query)
        except ServerSelectionTimeoutError:
            logger.error("Database connection error. Could not execute find_one.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during find_one: {e}")
            return None

    async def find_many(self, collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Finds multiple documents in a collection.

        Args:
            collection_name (str): The name of the collection to search.
            query (dict): The filter query to find documents.

        Returns:
            list: A list of found documents.
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.find(query)
            return await cursor.to_list(length=None)  # length=None to get all documents
        except ServerSelectionTimeoutError:
            logger.error("Database connection error. Could not execute find_many.")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during find_many: {e}")
            return []

    async def insert_one(self, collection_name: str, document: Dict[str, Any]) -> Optional[str]:
        """
        Inserts a single document into a collection.

        Args:
            collection_name (str): The name of the collection.
            document (dict): The document to insert.

        Returns:
            Optional[str]: The string representation of the inserted document's _id, or None on failure.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.insert_one(document)
            return str(result.inserted_id)
        except DuplicateKeyError:
            logger.warning(f"Attempted to insert a document with a duplicate key in '{collection_name}'.")
            return None
        except ServerSelectionTimeoutError:
            logger.error("Database connection error. Could not execute insert_one.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during insert_one: {e}")
            return None

    async def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Inserts multiple documents into a collection.

        Args:
            collection_name (str): The name of the collection.
            documents (list): A list of documents to insert.

        Returns:
            list: A list of inserted document IDs as strings.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.insert_many(documents)
            return [str(doc_id) for doc_id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error during insert_many: {e}")
            return []

    async def update_one(self, collection_name: str, query: Dict[str, Any], update_data: Dict[str, Any], upsert: bool = False) -> bool:
        """
        Updates a single document in a collection.

        Note: `update_data` should use MongoDB update operators (e.g., '$set', '$push').

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to find the document to update.
            update_data (dict): The update operations to apply.
            upsert (bool): If True, create a new document if no document matches the query.

        Returns:
            bool: True if a document was modified or upserted, False otherwise.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.update_one(query, update_data, upsert=upsert)
            return result.modified_count > 0 or result.upserted_id is not None
        except ServerSelectionTimeoutError:
            logger.error("Database connection error. Could not execute update_one.")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during update_one: {e}")
            return False

    async def update_many(self, collection_name: str, query: Dict[str, Any], update_data: Dict[str, Any], upsert: bool = False) -> int:
        """
        Updates multiple documents in a collection.

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to match documents.
            update_data (dict): Update operators (e.g., {"$set": {...}}).
            upsert (bool): If True, insert a new document if no match is found.

        Returns:
            int: Number of modified documents.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.update_many(query, update_data, upsert=upsert)
            return result.modified_count
        except Exception as e:
            logger.error(f"Error during update_many: {e}")
            return 0

    async def delete_one(self, collection_name: str, query: Dict[str, Any]) -> bool:
        """
        Deletes a single document from a collection.

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to find the document to delete.

        Returns:
            bool: True if a document was deleted, False otherwise.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(query)
            return result.deleted_count > 0
        except ServerSelectionTimeoutError:
            logger.error("Database connection error. Could not execute delete_one.")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during delete_one: {e}")
            return False

    async def delete_many(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Deletes multiple documents from a collection.

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to match documents.

        Returns:
            int: Number of deleted documents.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error during delete_many: {e}")
            return 0

    async def upsert(self, collection_name: str, query: Dict[str, Any], document: Dict[str, Any]) -> Optional[str]:
        """
        Updates a document if it exists, or inserts it if it does not.

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to find the document.
            document (dict): The data to set in the document.

        Returns:
            Optional[str]: The string representation of the upserted document's _id, or None on failure.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.update_one(query, {'$set': document}, upsert=True)
            if result.upserted_id:
                return str(result.upserted_id)
            # If an existing document was updated, we need to find it to return its ID.
            if result.modified_count > 0:
                updated_doc = await self.find_one(collection_name, query)
                return str(updated_doc['_id']) if updated_doc else None
            return None
        except ServerSelectionTimeoutError:
            logger.error("Database connection error. Could not execute upsert.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during upsert: {e}")
            return None

    async def replace_one(self, collection_name: str, query: Dict[str, Any], new_document: Dict[str, Any], upsert: bool = False) -> bool:
        """
        Replaces an entire document with a new one.

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to find the document.
            new_document (dict): The new document to replace with.
            upsert (bool): If True, insert if no match is found.

        Returns:
            bool: True if a document was replaced or inserted, False otherwise.
        """
        try:
            collection = self.db[collection_name]
            result = await collection.replace_one(query, new_document, upsert=upsert)
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Error during replace_one: {e}")
            return False

    async def find_with_projection(self, collection_name: str, query: Dict[str, Any], projection: Dict[str, int], sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """
        Finds documents with projection (select fields) and optional sorting.

        Args:
            collection_name (str): The name of the collection.
            query (dict): The filter to apply.
            projection (dict): Fields to include/exclude, e.g. {"field": 1, "other": 0}.
            sort (list): Optional sort spec, e.g. [("field", 1)] for ascending.

        Returns:
            list: Matching documents.
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.find(query, projection)
            if sort:
                cursor = cursor.sort(sort)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error during find_with_projection: {e}")
            return []

    async def count_documents(self, collection_name: str, query: Dict[str, Any]) -> int:
        """Returns the number of documents matching a query."""
        try:
            collection = self.db[collection_name]
            return await collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error during count_documents: {e}")
            return 0

    async def document_exists(self, collection_name: str, query: Dict[str, Any]) -> bool:
        """Checks if at least one document exists for a query."""
        try:
            collection = self.db[collection_name]
            doc = await collection.find_one(query, {"_id": 1})
            return doc is not None
        except Exception as e:
            logger.error(f"Error during document_exists: {e}")
            return False

    async def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Runs an aggregation pipeline."""
        try:
            collection = self.db[collection_name]
            cursor = collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error during aggregate: {e}")
            return []

    async def distinct(self, collection_name: str, field: str, query: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Gets distinct values for a field in documents matching query."""
        try:
            collection = self.db[collection_name]
            return await collection.distinct(field, query or {})
        except Exception as e:
            logger.error(f"Error during distinct: {e}")
            return []

    async def bulk_write(self, collection_name: str, operations: List[Any]) -> bool:
        """
        Executes bulk write operations (InsertOne, UpdateOne, DeleteOne, etc.).

        Example:
            ops = [
                InsertOne({"_id": 1, "name": "Alice"}),
                UpdateOne({"_id": 2}, {"$set": {"name": "Bob"}}, upsert=True),
                DeleteOne({"_id": 3})
            ]
        """
        try:
            collection = self.db[collection_name]
            result = await collection.bulk_write(operations)
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error during bulk_write: {e}")
            return False

    async def drop_collection(self, collection_name: str) -> bool:
        """Drops an entire collection."""
        try:
            await self.db.drop_collection(collection_name)
            return True
        except Exception as e:
            logger.error(f"Error during drop_collection: {e}")
            return False

    async def list_collections(self) -> List[str]:
        """Lists all collection names in the database."""
        try:
            return await self.db.list_collection_names()
        except Exception as e:
            logger.error(f"Error during list_collections: {e}")
            return []

    async def create_index(self, collection_name: str, keys: List[tuple], unique: bool = False) -> Optional[str]:
        """
        Creates an index on the given fields.

        Args:
            collection_name (str): The name of the collection.
            keys (list): A list of (field, direction) pairs, e.g. [("username", 1)].
            unique (bool): Whether the index should enforce uniqueness.

        Returns:
            str: The name of the created index.
        """
        try:
            collection = self.db[collection_name]
            return await collection.create_index(keys, unique=unique)
        except Exception as e:
            logger.error(f"Error during create_index: {e}")
            return None

    async def watch(self, collection_name: Optional[str] = None, pipeline: Optional[List[Dict[str, Any]]] = None):
        """
        Watches a collection (or the whole DB if collection_name is None) for real-time changes.

        Args:
            collection_name (str, optional): The collection to watch. If None, watch the entire DB.
            pipeline (list, optional): Aggregation pipeline to filter changes.

        Yields:
            dict: Change stream events.
        """
        try:
            target = self.db[collection_name] if collection_name else self.db
            async with target.watch(pipeline or []) as stream:
                async for change in stream:
                    yield change
        except Exception as e:
            logger.error(f"Error during watch: {e}")
