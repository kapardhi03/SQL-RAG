from typing import List, Literal

from pydantic import BaseModel, Field


class QuestionMetadata(BaseModel):
    question_type: Literal["factual", "inferential", "analytical", "multi_context"] = (
        Field(description="Question type")
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        description="Question difficulty"
    )
    required_context: str = Field(
        description="Specific quote string from the chunk needed to answer the question"
    )
    reasoning: str = Field(
        description="A brief description of how you arrived at the answer from the context"
    )


class QAPair(BaseModel):
    question: str
    metadata: QuestionMetadata
    answer: str


class QAPairList(BaseModel):
    qa_pairs: List[QAPair]


class EvaluationResponse(BaseModel):
    factual_accuracy: int = Field(description="Factual Accuracy (1-5)")
    completeness: int = Field(description="Completeness (1-5)")
    relevance: int = Field(description="Relevance (1-5)")
    hallucination: int = Field(description="Hallucination (1-5)")
    overall: int = Field(description="Overall Score (1-5)")
    justification: str = Field(description="Justification for the evaluation")
