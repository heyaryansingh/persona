"""Retrieval / RAG (v2, P4): pull the relevant papers on any question from a large corpus.

Dependency-light default (works now): MiniLM dense embeddings + TF-IDF lexical + RRF fusion
over a numpy working set. For scale/quality the plan (planning/VISION_AND_ROADMAP_V2.md §3)
swaps in MedCPT + FAISS + NCBI's precomputed 37M-abstract embeddings behind the same API.
"""
from .retriever import Embedder, Retriever

__all__ = ["Embedder", "Retriever"]
