from __future__ import annotations

from typing import List, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...services.advice_service import generate_advice

router = APIRouter(prefix="/advises", tags=["advises"])


class TechStack(BaseModel):
    languages: List[str] = Field(default_factory=list)
    webframes: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)


class StudentProfile(BaseModel):
    age: str = ""
    expectedSalaryBand: str = ""
    expectedTrack: str = ""


class ProProfile(BaseModel):
    years: str = ""
    salaryBand: str = ""
    track: str = ""


class OtherInfo(BaseModel):
    consentShare: str = ""
    isTruthful: str = ""
    note: str = ""


class AdvicePayload(BaseModel):
    techStack: TechStack
    profileType: Literal["student", "professional"]
    studentProfile: StudentProfile
    proProfile: ProProfile
    otherInfo: OtherInfo


class UserProfile(BaseModel):
    profileType: str
    workexpBin: str
    devtypeFamily: str
    track: str


class SalaryData(BaseModel):
    currency: str
    fx: str
    level: str
    n: int
    confidence: str
    minN: int
    isMarketRef: bool
    p25Usd: float
    p50Usd: float
    p75Usd: float
    p90Usd: float
    p25: float
    p50: float
    p75: float
    p90: float
    userSalaryBand: dict = None


class TechItem(BaseModel):
    tech: str
    gap: float = None
    want: float = None
    have: float = None


class TechCategory(BaseModel):
    mainstream: List[TechItem]
    gap: List[TechItem]
    chosen: List[TechItem]


class TechThresholds(BaseModel):
    baseMinWant: float
    mainstreamUsedThr: float
    gapUsedThr: float


class TechData(BaseModel):
    cohort: dict
    thresholds: dict
    language: TechCategory
    database: TechCategory
    webframe: TechCategory


class AdvancementItem(BaseModel):
    tech: str
    currentHave: float
    targetHave: float
    lift: float


class AdvancementData(BaseModel):
    currentLevel: str
    targetLevel: str
    available: bool
    language: List[AdvancementItem]
    database: List[AdvancementItem]
    webframe: List[AdvancementItem]


class AdviceResponse(BaseModel):
    userProfile: UserProfile
    salary: SalaryData = None
    tech: TechData
    advancement: AdvancementData = None


def _validate(p: AdvicePayload) -> None:
    missing = []
    if not p.techStack.languages:
        missing.append("语言/基础能力掌握情况")
    if not p.techStack.databases:
        missing.append("数据库掌握情况")
    if not p.techStack.webframes:
        missing.append("Web/框架/平台掌握情况")

    if p.profileType == "student":
        if not p.studentProfile.age.strip():
            missing.append("学生-年龄")
        if not p.studentProfile.expectedSalaryBand.strip():
            missing.append("学生-期望薪资区间")
        if not p.studentProfile.expectedTrack.strip():
            missing.append("学生-期望方向")
    else:
        if not p.proProfile.years.strip():
            missing.append("从业者-工作年份")
        if not p.proProfile.salaryBand.strip():
            missing.append("从业者-当前薪资区间")
        if not p.proProfile.track.strip():
            missing.append("从业者-方向")

    if not p.otherInfo.consentShare.strip():
        missing.append("是否愿意分享数据")
    if not p.otherInfo.isTruthful.strip():
        missing.append("信息真实程度")

    if missing:
        raise HTTPException(status_code=400, detail=f"请先填写：{missing[0]}")


@router.post("/personal-advice/generate", response_model=AdviceResponse)
def generate_personal_advice(payload: AdvicePayload) -> AdviceResponse:
    _validate(payload)
    try:
        result = generate_advice(payload.model_dump())
        return AdviceResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
