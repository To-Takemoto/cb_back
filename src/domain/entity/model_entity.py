from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ModelArchitecture:
    input_modalities: List[str]
    output_modalities: List[str] 
    tokenizer: str


@dataclass
class ModelPricing:
    prompt: str
    completion: str


@dataclass
class ModelEntity:
    id: str
    name: str
    created: int
    description: Optional[str] = None
    architecture: Optional[ModelArchitecture] = None
    pricing: Optional[ModelPricing] = None
    context_length: Optional[int] = None