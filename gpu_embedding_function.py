"""
Custom GPU-Enabled Embedding Function for ChromaDB
Workaround for ChromaDB's SentenceTransformerEmbeddingFunction device parameter bug
"""

import torch
from sentence_transformers import SentenceTransformer
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from typing import cast

class GPUSentenceTransformerEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Custom embedding function that properly uses GPU for SentenceTransformer models.
    This works around ChromaDB's bug where the device parameter is ignored.
    """
    
    def __init__(self, model_name: str, device: str = None, normalize_embeddings: bool = False):
        """
        Initialize the embedding function.
        
        Args:
            model_name: Name of the SentenceTransformer model
            device: Device to use ('cuda', 'cpu', or None for auto-detection)
            normalize_embeddings: Whether to normalize embeddings
        """
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.model_name = model_name
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        
        # Initialize the model with the specified device
        self.model = SentenceTransformer(model_name, device=device)
        
        print(f"[GPU Embedding Function] Model: {model_name}")
        print(f"[GPU Embedding Function] Device: {self.model.device}")
        print(f"[GPU Embedding Function] Normalize: {normalize_embeddings}")
    
    def __call__(self, input: Documents) -> Embeddings:
        """
        Encode the input documents into embeddings.
        
        Args:
            input: List of documents to encode
            
        Returns:
            List of embeddings
        """
        # Encode using the SentenceTransformer model
        embeddings = self.model.encode(
            input,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True
        )
        
        # Convert to list format expected by ChromaDB
        return cast(Embeddings, embeddings.tolist())
    
    def get_model_info(self) -> dict:
        """Get information about the model."""
        return {
            "model_name": self.model_name,
            "device": str(self.model.device),
            "normalize_embeddings": self.normalize_embeddings,
            "embedding_dim": self.model.get_sentence_embedding_dimension()
        }


# Alternative: Direct replacement function
def create_gpu_embedding_function(model_name: str = "all-MiniLM-L6-v2", device: str = None):
    """
    Factory function to create a GPU-enabled embedding function.
    
    Args:
        model_name: Name of the SentenceTransformer model
        device: Device to use ('cuda', 'cpu', or None for auto-detection)
        
    Returns:
        GPUSentenceTransformerEmbeddingFunction instance
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    return GPUSentenceTransformerEmbeddingFunction(
        model_name=model_name,
        device=device,
        normalize_embeddings=False
    ) 