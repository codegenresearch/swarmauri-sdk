import logging
import chromadb
from chromadb.config import Settings

from typing import List, Union, Literal

from swarmauri.documents.concrete.Document import Document
from swarmauri.embeddings.concrete.Doc2VecEmbedding import Doc2VecEmbedding
from swarmauri.distances.concrete.CosineDistance import CosineDistance

from swarmauri.vector_stores.base.VectorStoreBase import VectorStoreBase
from swarmauri.vector_stores.base.VectorStoreRetrieveMixin import (
    VectorStoreRetrieveMixin,
)
from swarmauri.vector_stores.base.VectorStoreSaveLoadMixin import (
    VectorStoreSaveLoadMixin,
)
from swarmauri.vector_stores.base.VectorStorePersistentMixin import (
    VectorStorePersistentMixin,
)


class PersistentChromaDBVectorStore(
    VectorStoreSaveLoadMixin,
    VectorStoreRetrieveMixin,
    VectorStorePersistentMixin,
    VectorStoreBase,
):
    type: Literal["PersistentChromaDBVectorStore"] = "PersistentChromaDBVectorStore"

    def __init__(
        self,
        collection_name: str,
        vector_size: int,
        path: str = "./chromadb_data",
        **kwargs,
    ):
        """
        Initialize the PersistentChromaDBVectorStore.

        Args:
            collection_name (str): The name of the collection.
            vector_size (int): The size of the vectors.
            path (str): The directory where ChromaDB will store its data files.
        """
        super().__init__(
            collection_name=collection_name,
            path=path,
            vector_size=vector_size,
            **kwargs,
        )

        self._embedder = Doc2VecEmbedding(vector_size=vector_size)
        self._distance = CosineDistance()
        self.vectorizer = self._embedder

        self.collection_name = collection_name
        self.path = path

        # Initialize the client and collection later in the connect method
        self.client = None
        self.collection = None

    def connect(self) -> None:
        """
        Establish a connection to ChromaDB and get or create the collection.
        """
        settings = Settings(
            chroma_api_impl="chromadb.api.fastapi.FastAPI",  # Use FastAPI if LocalAPI is not supported
            chroma_server_host="localhost",  # Server host
            chroma_server_http_port=8000,  # Server port
        )

        self.client = chromadb.Client(
            settings=settings,
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        logging.info(
            f"Connected to ChromaDB at {self.path}, collection: {self.collection_name}"
        )

    def disconnect(self) -> None:
        """
        Close the connection to ChromaDB.
        """
        if self.client:
            # Perform any necessary cleanup here
            self.client = None
            self.collection = None

    def add_document(self, document: Document) -> None:
        embedding = None
        if not document.embedding:
            self.vectorizer.fit([document.content])  # Fit only once
            embedding = (
                self.vectorizer.transform([document.content])[0].to_numpy().tolist()
            )
        else:
            embedding = document.embedding

        self.collection.add(
            ids=[document.id],
            documents=[document.content],
            embeddings=[embedding],
            metadatas=[document.metadata],
        )

    def add_documents(self, documents: List[Document]) -> None:
        ids = [doc.id for doc in documents]
        texts = [doc.content for doc in documents]
        embeddings = [
            self._embedder.infer_vector(doc.content).value for doc in documents
        ]
        metadatas = [doc.metadata for doc in documents]

        self.collection.add(
            ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas
        )

    def get_document(self, doc_id: str) -> Union[Document, None]:
        results = self.collection.get(ids=[doc_id])
        if results["ids"]:
            document = Document(
                id=results["ids"][0],
                content=results["documents"][0],
                metadata=results["metadatas"][0],
            )
            return document
        return None

    def get_all_documents(self) -> List[Document]:
        results = self.collection.get()
        documents = [
            Document(
                id=results["ids"][idx],
                content=results["documents"][idx],
                metadata=results["metadatas"][idx],
            )
            for idx in range(len(results["ids"]))
        ]
        return documents

    def delete_document(self, doc_id: str) -> None:
        self.collection.delete(ids=[doc_id])

    def update_document(self, doc_id: str, updated_document: Document) -> None:
        document_vector = None
        # Precompute the embedding outside the update process
        if not updated_document.embedding:
            # Transform without refitting to avoid vocabulary issues
            document_vector = self.vectorizer.transform([updated_document.content])[0]
        else:
            document_vector = updated_document.embedding

        document_vector = document_vector.to_numpy().tolist()

        updated_document.embedding = document_vector

        self.delete_document(doc_id)
        self.add_document(updated_document)

    def clear_documents(self) -> None:
        documents = self.get_all_documents()
        doc_ids = [doc.id for doc in documents]
        self.collection.delete(ids=doc_ids)

    def document_count(self) -> int:
        return len(self.get_all_documents())

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        query_embedding = self._embedder.infer_vector(query).value
        print(query_embedding)

        results = self.collection.query(
            query_embeddings=query_embedding, n_results=top_k
        )

        print(results)
        return [
            Document(
                id=results["ids"][0][idx],
                content=results["documents"][0][idx],
                metadata=results["metadatas"][0][idx],
            )
            for idx in range(len(results["ids"]))
        ]
