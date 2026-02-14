from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str

class UserResponse(BaseModel):
    id: int
    username: str
    questionnaire_answers: Optional[dict] = None

    class Config:
        from_attributes = True

class QuestionnaireSubmit(BaseModel):
    Q1: Optional[str] = None   # 公钥地址
    Q2: Optional[str] = None   # 性别
    Q3: Optional[str] = None   # 年龄
    Q4: Optional[str] = None   # 职业
    Q5: Optional[str] = None   # 原生家庭农业 A/B/C
    Q6: Optional[str] = None   # 认识的朋友 A/B/C
    Q7: Optional[str] = None   # 加密货币 A/B/C
    Q8: Optional[str] = None   # DAO投票 A/B
    Q9: Optional[str] = None   # 冒险 0-10
    Q10: Optional[str] = None  # 选择 A/B
    Q11: Optional[str] = None # 信任 A/B
    Q12: Optional[str] = None # 环保意愿 A/B/C/D

class GameCreate(BaseModel):
    game_code: str

class GameResponse(BaseModel):
    id: int
    game_code: str
    creator_id: Optional[int] = None
    status: str
    current_round: int
    phase: int
    
    class Config:
        from_attributes = True

class PlayerResponse(BaseModel):
    id: int
    user_id: int
    username: str
    current_nt: float
    current_env: float
    
    class Config:
        from_attributes = True

class RoundChoice(BaseModel):
    choice: str  # "organic" or "inorganic"
    apply_subsidy: bool = False
    vote_target_id: Optional[int] = None

class RoundResult(BaseModel):
    round_number: int
    phase: int
    nt_before: float
    nt_after: float
    env_before: float
    env_after: float
    round_nt_earned: float
    env_change: str  # "增强" or "减弱"
    subsidy_result: Optional[str] = None  # "通过", "识破", None

class GameState(BaseModel):
    game_id: int
    current_round: int
    phase: int
    status: str
    players: List[PlayerResponse]
    my_player: Optional[PlayerResponse] = None
    round_results: Optional[List[RoundResult]] = None

class BroadcastMessage(BaseModel):
    type: str  # "subsidy_applied", "subsidy_caught", "vote_result", "round_complete"
    message: str
    data: Optional[dict] = None
