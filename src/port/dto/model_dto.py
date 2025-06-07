from typing import List, Optional
from pydantic import BaseModel


class ModelArchitectureDto(BaseModel):
    input_modalities: List[str]
    output_modalities: List[str]
    tokenizer: str


class ModelPricingDto(BaseModel):
    prompt: str
    completion: str


class ModelDto(BaseModel):
    id: str
    name: str
    created: int
    description: Optional[str] = None
    architecture: Optional[ModelArchitectureDto] = None
    pricing: Optional[ModelPricingDto] = None
    context_length: Optional[int] = None


class ModelListResponseDto(BaseModel):
    data: List[ModelDto]


class ModelSelectionRequestDto(BaseModel):
    model_id: str