from pydantic import BaseModel, Field


class CaseRequest(BaseModel):
    case_id: str = Field("demo_001")


class ApprovalRequest(BaseModel):
    case_id: str = Field("demo_001")
    approved: bool = Field(False)
    approver: str = Field("engineer")


class PipelineRequest(BaseModel):
    case_id: str = Field("demo_001")
    approved: bool = Field(False)
    max_iterations: int = Field(5, ge=1, le=20)


class FeedbackRequest(BaseModel):
    case_id: str = Field("demo_001")
    iteration_index: int = Field(0)
    ai_suggestion: dict = Field(default_factory=dict)
    engineer_final_decision: dict = Field(default_factory=dict)
    reason: str = ""
    engineer: str = "engineer"
