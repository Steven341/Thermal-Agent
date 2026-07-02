from pydantic import BaseModel, Field, field_validator
from tools.io_utils import validate_case_id


class CaseIdMixin(BaseModel):
    @field_validator("case_id", check_fields=False)
    @classmethod
    def _validate_case_id(cls, value: str) -> str:
        return validate_case_id(value)


class CaseRequest(CaseIdMixin):
    case_id: str = Field("demo_001")


class ApprovalRequest(CaseIdMixin):
    case_id: str = Field("demo_001")
    approved: bool = Field(False)
    approver: str = Field("engineer")


class PipelineRequest(CaseIdMixin):
    case_id: str = Field("demo_001")
    approved: bool = Field(False)
    max_iterations: int = Field(5, ge=1, le=20)


class FeedbackRequest(CaseIdMixin):
    case_id: str = Field("demo_001")
    iteration_index: int = Field(0)
    ai_suggestion: dict = Field(default_factory=dict)
    engineer_final_decision: dict = Field(default_factory=dict)
    reason: str = ""
    engineer: str = "engineer"
