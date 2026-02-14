"""
游戏核心逻辑：收益计算、生态值影响、识破机制等
所有数值均在此处以常量定义，避免 magic number。
"""
import random
from typing import Dict, List, Tuple

# ========== 初始状态 ==========
INITIAL_NT = 10.0
INITIAL_ENV = 0.0

# ========== 基础收益（每轮 NT） ==========
ORGANIC_BASE_NT = 3.0
INORGANIC_BASE_NT = 6.0

# ========== 每轮 ENV 对 NT 收益的影响（第一轮之后生效） ==========
# 每 10 ENV 影响 0.5 NT：当前 ENV 20 → +1 NT，ENV -10 → -0.5 NT
ENV_NT_BONUS_RATE = 0.05  # 每 1 ENV → ±0.05 NT
# 环境值影响的 NT 加减封顶：不超过基础收益的 -50% ～ +200%
# 有机肥 3：最多减 1.5、最多加 6；无机肥 6：最多减 3、最多加 12
ENV_BONUS_MIN_RATIO = 0.5   # 最多减少 = base * 50%
ENV_BONUS_MAX_RATIO = 1.0   # 最多增加 = base * 100%

# ========== 生态值变化（每轮 ENV 变化量） ==========
ENV_SELF_ORGANIC = 4.0      # 自己选有机肥：自己 +1.0
ENV_SELF_INORGANIC = -4.0   # 自己选无机肥：自己 -1
ENV_OTHERS_ORGANIC = 1    # 他人选有机肥：对自己 +0.5
ENV_OTHERS_INORGANIC = -1 # 他人选无机肥：对自己 -0.5

# ========== 最终结算：生态值折算为 NT（仅 15 轮结束后） ==========
FINAL_ENV_POSITIVE_RATE = 0.5   # 正生态每 1 点 = +0.5 NT
FINAL_ENV_NEGATIVE_RATE = 1.0  # 负生态每 -1 点 = -1 NT

# ========== 补贴金额（质押/补贴 NT） ==========
PHASE2_SUBSIDY = 1.5
PHASE3_SUBSIDY = 2.0

# ========== 识破概率（无机肥申领补贴时） ==========
PHASE2_CATCH_PROBABILITY = 0.3
PHASE3_CATCH_PROBABILITY = 0.5

# ========== 房间人数上限 ==========
MAX_PLAYERS_PER_GAME = 99

def calculate_earnings(choice: str, current_env: float = 0.0) -> float:
    """
    计算本轮收益。基础收益 + 当前环境值对 NT 的影响（每 10 ENV = 0.5 NT），
    环境影响封顶：加减不超过基础收益的 50%～200%（有机肥 ±1.5～6，无机肥 ±3～12）。
    最终结算（15 轮结束后 ENV→NT）仍按 FINAL_ENV_* 单独计算。
    
    Args:
        choice: "organic" 或 "inorganic"
        current_env: 该玩家在本轮开始时的环境值（第一轮后开始影响）
    
    Returns:
        本轮 base + clamp(env_bonus, -base*50%, base*200%)
    """
    base = ORGANIC_BASE_NT if choice == "organic" else INORGANIC_BASE_NT
    raw_bonus = current_env * ENV_NT_BONUS_RATE
    min_bonus = -base * ENV_BONUS_MIN_RATIO
    max_bonus = base * ENV_BONUS_MAX_RATIO
    bonus = max(min_bonus, min(max_bonus, raw_bonus))
    return base + bonus

def calculate_env_change(choice: str, player_id: int, all_choices: Dict[int, str]) -> float:
    """
    计算生态值变化
    
    Args:
        choice: 当前玩家的选择
        player_id: 当前玩家ID
        all_choices: 所有玩家的选择 {player_id: choice}
    
    Returns:
        生态值变化量
    """
    env_change = 0.0
    
    # 自己的选择影响
    if choice == "organic":
        env_change += ENV_SELF_ORGANIC
    else:  # inorganic
        env_change += ENV_SELF_INORGANIC
    
    # 其他人的选择影响
    for pid, c in all_choices.items():
        if pid != player_id:
            if c == "organic":
                env_change += ENV_OTHERS_ORGANIC
            else:  # inorganic
                env_change += ENV_OTHERS_INORGANIC
    
    return env_change

def check_subsidy_verification(choice: str, phase: int, is_voted: bool = False) -> bool:
    """
    检查补贴验证结果
    
    Args:
        choice: 玩家选择的肥料类型
        phase: 游戏阶段 (2 或 3)
        is_voted: 是否被投票质疑
    
    Returns:
        True=通过验证, False=被识破
    """
    # 如果选择有机肥，总是通过
    if choice == "organic":
        return True
    
    # 如果被投票质疑，100%识破
    if is_voted:
        return False
    
    # 无机肥申请补贴的识破概率
    if phase == 2:
        return random.random() >= PHASE2_CATCH_PROBABILITY
    elif phase == 3:
        return random.random() >= PHASE3_CATCH_PROBABILITY
    
    return True

def final_settlement(nt: float, env: float) -> float:
    """
    最终结算：将生态值转换为NT（仅 15 轮结束后调用）
    
    Args:
        nt: 当前NT数量
        env: 当前生态值
    
    Returns:
        最终NT数量
    """
    if env > 0:
        nt += env * FINAL_ENV_POSITIVE_RATE
    else:
        nt += env * FINAL_ENV_NEGATIVE_RATE
    return nt

def get_env_change_text(env_change: float) -> str:
    """
    获取生态值变化文本（用于Phase 1显示）
    
    Returns:
        "增强" 或 "减弱"
    """
    return "增强" if env_change > 0 else "减弱"
