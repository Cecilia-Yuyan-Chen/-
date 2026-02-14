"""
FastAPI主应用
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Any
import json
import random
import string
from datetime import datetime

from app.models import (
    Base, engine, SessionLocal, init_db,
    User, Game, GamePlayer, GameRound, GameVote
)
from app.schemas import (
    UserCreate, UserResponse, GameResponse, PlayerResponse,
    RoundChoice, RoundResult, GameState, BroadcastMessage, QuestionnaireSubmit
)
from app.game_logic import (
    calculate_earnings, calculate_env_change, check_subsidy_verification,
    final_settlement, get_env_change_text, PHASE2_SUBSIDY, PHASE3_SUBSIDY,
    FINAL_ENV_POSITIVE_RATE, FINAL_ENV_NEGATIVE_RATE,
    INITIAL_NT, INITIAL_ENV, MAX_PLAYERS_PER_GAME,
)
from app.websocket import manager
from app.excel_export import export_game_to_excel

app = FastAPI(title="迷雾南塘游戏API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
init_db()

# 依赖注入：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 游戏状态管理（内存中）
game_states: Dict[int, Dict] = {}  # {game_id: {player_id: choice_data}}
# Phase 2/3：等待所有人点击「下一轮」再进入下一轮
ready_for_next_round_states: Dict[tuple, set] = {}  # (game_id, round_number) -> set of player_id
# Phase 3：每轮两条广播（投票结果 + 系统识破）一起在结果页展示
phase3_round_broadcasts: Dict[tuple, list] = {}  # (game_id, round_number) -> list of {type, message, ...}

@app.get("/")
async def root():
    return {"message": "迷雾南塘游戏API"}

# ========== 用户相关 ==========

def _user_to_response(user: User) -> dict:
    """将 User 转为 API 响应（questionnaire_answers 从 JSON 字符串解析）"""
    q = None
    if getattr(user, "questionnaire_answers", None):
        try:
            q = json.loads(user.questionnaire_answers)
        except (TypeError, json.JSONDecodeError):
            q = None
    return {"id": user.id, "username": user.username, "questionnaire_answers": q}


@app.post("/api/users/register")
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """注册/登录：用户名为唯一标识，存在则返回该用户，否则创建新用户"""
    name = (user_data.username or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    existing_user = db.query(User).filter(User.username == name).first()
    if existing_user:
        return _user_to_response(existing_user)
    new_user = User(username=name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _user_to_response(new_user)


@app.get("/api/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _user_to_response(user)


@app.post("/api/users/{user_id}/questionnaire")
async def submit_questionnaire(user_id: int, data: QuestionnaireSubmit, db: Session = Depends(get_db)):
    """提交问卷 Q1–Q12，保存到用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    payload = data.model_dump(exclude_none=True)
    user.questionnaire_answers = json.dumps(payload, ensure_ascii=False)
    db.commit()
    return {"message": "问卷已保存"}

# ========== 游戏相关 ==========

def generate_game_code() -> str:
    """生成游戏房间号"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.post("/api/games/create")
async def create_game(user_id: int = None, username: str = None, db: Session = Depends(get_db)):
    """创建新游戏：优先使用 user_id（关联用户表唯一昵称），否则用 username 作为本局昵称"""
    game_code = generate_game_code()
    new_game = Game(game_code=game_code, status="waiting", creator_id=None)
    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    if user_id:
        u = db.query(User).filter(User.id == user_id).first()
        name = (u.username if u else "").strip() or "房主"
    else:
        name = (username or "").strip() or "房主"
    creator_player = GamePlayer(
        game_id=new_game.id,
        user_id=user_id if user_id else None,
        username=name,
        initial_nt=INITIAL_NT,
        current_nt=INITIAL_NT,
        current_env=INITIAL_ENV
    )
    db.add(creator_player)
    db.commit()
    db.refresh(creator_player)
    
    new_game.creator_id = creator_player.id
    db.commit()
    db.refresh(new_game)
    
    game_states[new_game.id] = {}
    return {
        "id": new_game.id,
        "game_code": new_game.game_code,
        "creator_id": new_game.creator_id,
        "status": new_game.status,
        "current_round": new_game.current_round,
        "phase": new_game.phase,
        "player_id": creator_player.id,
    }

@app.post("/api/games/{game_id}/join")
async def join_game(
    game_id: int,
    user_id: int = None,
    username: str = None,
    db: Session = Depends(get_db)
):
    """加入游戏：优先使用 user_id。若游戏已开始/已结束，且该 user 曾在此房间，则允许重新连接（复入）"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")

    # 游戏已开始或已结束：只允许「重新连接」——该 user 在此局已有玩家记录则返回原 player_id
    if game.status != "waiting":
        if user_id:
            existing = db.query(GamePlayer).filter(
                GamePlayer.game_id == game_id,
                GamePlayer.user_id == user_id
            ).first()
            if existing:
                return {"player_id": existing.id, "message": "重新连接成功", "rejoined": True}
        raise HTTPException(
            status_code=400,
            detail="游戏已开始或已结束。若您之前在此房间中，请使用同一账号重新进入以继续游戏。"
        )

    # 等待中：同一 user 已在此房间则复入，不创建重复玩家
    if user_id:
        existing = db.query(GamePlayer).filter(
            GamePlayer.game_id == game_id,
            GamePlayer.user_id == user_id
        ).first()
        if existing:
            return {"player_id": existing.id, "message": "您已在此房间中", "rejoined": True}

    players_count = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).count()
    if players_count >= MAX_PLAYERS_PER_GAME:
        raise HTTPException(status_code=400, detail=f"房间已满（最多 {MAX_PLAYERS_PER_GAME} 人）")
    if user_id:
        u = db.query(User).filter(User.id == user_id).first()
        name = (u.username if u else "").strip() or "玩家"
    else:
        name = (username or "").strip() or "玩家"
    new_player = GamePlayer(
        game_id=game_id,
        user_id=user_id if user_id else None,
        username=name,
        initial_nt=INITIAL_NT,
        current_nt=INITIAL_NT,
        current_env=INITIAL_ENV
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    
    return {"player_id": new_player.id, "message": "成功加入游戏"}

@app.get("/api/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: int, db: Session = Depends(get_db)):
    """获取游戏信息"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return game

@app.get("/api/games/by-code/{game_code}", response_model=GameResponse)
async def get_game_by_code(game_code: str, db: Session = Depends(get_db)):
    """根据 6 位房间号获取游戏（用于加入房间）"""
    game = db.query(Game).filter(Game.game_code == game_code.strip().upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="房间号不存在，请检查后重试")
    return game

def _player_display_name(player, db):
    if getattr(player, "username", None) and str(player.username).strip():
        return (player.username or "").strip()
    if player.user_id:
        user = db.query(User).filter(User.id == player.user_id).first()
        return user.username if user else f"玩家{player.id}"
    return f"玩家{player.id}"

@app.get("/api/games/{game_id}/players")
async def get_game_players(game_id: int, db: Session = Depends(get_db)):
    """获取游戏玩家列表；同一 user_id 只返回一条（去重），游戏结束时含结算前NT、生态值、生态结算、最终NT"""
    game = db.query(Game).filter(Game.id == game_id).first()
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    result = []
    seen_user_ids = set()
    for player in players:
        uid = getattr(player, "user_id", None)
        if uid is not None and uid in seen_user_ids:
            continue
        if uid is not None:
            seen_user_ids.add(uid)
        item = {
            "id": player.id,
            "user_id": uid,
            "username": _player_display_name(player, db),
            "current_nt": player.current_nt,
            "current_env": player.current_env,
        }
        if game and game.status == "finished" and player.final_nt is not None and player.final_env is not None:
            env_settlement = (player.final_env * FINAL_ENV_POSITIVE_RATE if player.final_env > 0 else player.final_env * FINAL_ENV_NEGATIVE_RATE)
            item["nt_before_settlement"] = player.final_nt - env_settlement
            item["final_env"] = player.final_env
            item["env_settlement"] = env_settlement
            item["final_nt"] = player.final_nt
            item["is_winner"] = getattr(player, "is_winner", False)
        result.append(item)
    return result

@app.post("/api/games/{game_id}/start")
async def start_game(game_id: int, player_id: int, db: Session = Depends(get_db)):
    """开始游戏（仅房间创建者可调用，传当前玩家的 player_id）"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    
    if game.creator_id is not None and game.creator_id != player_id:
        raise HTTPException(status_code=403, detail="只有房间创建者可以开始游戏")
    
    if game.status != "waiting":
        raise HTTPException(status_code=400, detail="游戏已开始")
    
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    if len(players) < 2:
        raise HTTPException(status_code=400, detail="玩家数量不足")
    
    game.status = "playing"
    game.current_round = 1
    game.phase = 1
    db.commit()
    
    # 广播游戏开始
    await manager.broadcast_to_all_in_game({
        "type": "game_started",
        "message": "游戏开始！",
        "game_id": game_id,
        "current_round": 1,
        "phase": 1
    }, game_id)
    
    return {"message": "游戏已开始", "current_round": 1, "phase": 1}

# ========== WebSocket连接 ==========

@app.websocket("/ws/game/{game_id}/player/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int, player_id: int):
    """WebSocket连接端点"""
    await manager.connect(websocket, game_id, player_id)
    try:
        while True:
            data = await websocket.receive_json()
            # 处理WebSocket消息
            await handle_websocket_message(game_id, player_id, data)
    except WebSocketDisconnect:
        manager.disconnect(game_id, player_id)

async def handle_websocket_message(game_id: int, player_id: int, data: dict):
    """处理WebSocket消息"""
    message_type = data.get("type")
    
    if message_type == "submit_choice":
        await handle_submit_choice(game_id, player_id, data)
    elif message_type == "submit_vote":
        await handle_submit_vote(game_id, player_id, data)
    elif message_type == "ready_for_next_round":
        await handle_ready_for_next_round(game_id, player_id, data)

async def handle_ready_for_next_round(game_id: int, player_id: int, data: dict):
    """Phase 2：所有人点击「下一轮」后才进入下一轮"""
    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game or game.status != "playing":
            return
        round_number = game.current_round
        key = (game_id, round_number)
        if key not in ready_for_next_round_states:
            return
        ready_for_next_round_states[key].add(player_id)
        players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
        if len(ready_for_next_round_states[key]) >= len(players):
            ready_for_next_round_states.pop(key, None)
            await check_next_round_or_phase(game_id, db)
    finally:
        db.close()

async def handle_submit_choice(game_id: int, player_id: int, data: dict):
    """处理玩家提交选择"""
    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game or game.status != "playing":
            return
        
        choice = data.get("choice")  # "organic" or "inorganic"
        apply_subsidy = data.get("apply_subsidy", False)
        
        # 保存选择
        if game_id not in game_states:
            game_states[game_id] = {}
        game_states[game_id][player_id] = {
            "choice": choice,
            "apply_subsidy": apply_subsidy,
            "submitted": True
        }
        
        # 广播「谁已选择」给房间内所有人，方便大家看到进度
        await manager.broadcast_to_all_in_game({
            "type": "submission_status",
            "submitted_player_ids": list(game_states[game_id].keys())
        }, game_id)
        
        # 检查是否所有玩家都已提交
        players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
        all_submitted = len(game_states[game_id]) == len(players)
        
        if all_submitted:
            # 处理本轮结果
            await process_round(game_id, db)
    finally:
        db.close()

async def handle_submit_vote(game_id: int, player_id: int, data: dict):
    """处理投票"""
    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game or game.status != "playing" or game.phase != 3:
            return
        
        target_id = data.get("target_id")  # 0 或缺失表示「谁都不选」，记入 Excel 为 0
        round_number = game.current_round
        
        # 检查是否已投票
        existing_vote = db.query(GameVote).filter(
            GameVote.game_id == game_id,
            GameVote.round_number == round_number,
            GameVote.voter_id == player_id
        ).first()
        
        if existing_vote:
            return
        
        # 创建投票（target_id 为 None 表示谁都不选，导出 Excel 时写 0）
        vote = GameVote(
            game_id=game_id,
            round_number=round_number,
            voter_id=player_id,
            target_id=int(target_id) if target_id else None
        )
        db.add(vote)
        db.commit()
        
        # 广播「谁已投票」给房间内所有人
        votes = db.query(GameVote).filter(
            GameVote.game_id == game_id,
            GameVote.round_number == round_number
        ).all()
        await manager.broadcast_to_all_in_game({
            "type": "vote_submission_status",
            "submitted_player_ids": [v.voter_id for v in votes]
        }, game_id)
        
        # 检查是否所有玩家都已投票
        players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
        if len(votes) == len(players):
            # 处理投票结果
            await process_voting_phase(game_id, db)
    finally:
        db.close()

async def process_round(game_id: int, db: Session):
    """处理一轮游戏"""
    game = db.query(Game).filter(Game.id == game_id).first()
    round_number = game.current_round
    phase = game.phase
    
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    choices = game_states[game_id]
    
    # 收集所有选择
    all_choices = {}
    for player in players:
        if player.id in choices:
            all_choices[player.id] = choices[player.id]["choice"]
    
    # 处理每个玩家的收益
    round_results = {}
    
    for player in players:
        if player.id not in choices:
            continue
        
        choice_data = choices[player.id]
        choice = choice_data["choice"]
        apply_subsidy = choice_data.get("apply_subsidy", False)
        
        # 计算收益和生态值变化（收益含当前 ENV 影响：每 10 ENV = 0.5 NT）
        env_change = calculate_env_change(choice, player.id, all_choices)
        earnings = calculate_earnings(choice, player.current_env)
        
        # 补贴处理（Phase 2和3）
        subsidy_amount = 0
        subsidy_verified = None
        if apply_subsidy and phase >= 2:
            subsidy_amount = PHASE2_SUBSIDY if phase == 2 else PHASE3_SUBSIDY
            
            # 先扣除质押
            earnings -= subsidy_amount
            
            # Phase 3的补贴验证在投票后处理
            if phase == 3:
                # 暂时不处理补贴，等投票完成后再处理
                pass
            else:
                # Phase 2: 立即验证
                subsidy_verified = check_subsidy_verification(choice, phase)
                if subsidy_verified:
                    # 验证通过，返还质押并获得补贴
                    earnings += subsidy_amount * 2
                else:
                    # 被识破，质押被罚没（已经扣除了，不需要再扣）
                    pass
        
        # 更新玩家数据
        nt_before = player.current_nt
        env_before = player.current_env
        
        player.current_nt += earnings
        player.current_env += env_change
        
        nt_after = player.current_nt
        env_after = player.current_env
        
        # 保存轮次数据
        round_record = GameRound(
            game_id=game_id,
            round_number=round_number,
            phase=phase,
            player_id=player.id,
            choice=choice,
            applied_subsidy=apply_subsidy,
            subsidy_verified=subsidy_verified,
            nt_before=nt_before,
            nt_after=nt_after,
            env_before=env_before,
            env_after=env_after,
            round_nt_earned=earnings
        )
        db.add(round_record)
        
        round_results[player.id] = {
            "nt_before": nt_before,
            "nt_after": nt_after,
            "env_before": env_before,
            "env_after": env_after,
            "round_nt_earned": earnings,
            "env_change": get_env_change_text(env_change),
            "subsidy_result": None
        }
    
    db.commit()
    
    # Phase 3: 先保存基础数据，然后进入投票阶段
    if phase == 3:
        # 先保存基础收益（不含补贴）
        db.commit()
        # 广播补贴申请，然后进入投票阶段
        await process_phase3_subsidy_broadcast(game_id, round_number, choices, db)
        # 投票阶段由handle_submit_vote触发，投票完成后会调用process_phase3_final_calculation
        return
    
    # Phase 2: 处理补贴申请和广播，然后等待所有人点击「下一轮」
    if phase == 2:
        await process_phase2_broadcast(game_id, round_number, choices, round_results, db)
        ready_for_next_round_states[(game_id, round_number)] = set()
        return
    
    # Phase 1: 直接显示结果
    if phase == 1:
        await broadcast_round_results(game_id, round_results, phase, round_number)
    
    # 检查是否进入下一轮或下一阶段
    await check_next_round_or_phase(game_id, db)

async def process_phase2_broadcast(game_id: int, round_number: int, choices: dict, round_results: dict, db: Session):
    """处理Phase 2的广播：一条消息包含申请补贴与识破名单，所有人看到一致"""
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    
    subsidy_applicants = []
    for player in players:
        if player.id in choices and choices[player.id].get("apply_subsidy"):
            subsidy_applicants.append({"player_id": player.id, "username": _player_display_name(player, db)})
    
    caught_players = []
    for player in players:
        if player.id in choices:
            choice_data = choices[player.id]
            if choice_data.get("apply_subsidy") and choice_data.get("choice") == "inorganic":
                round_record = db.query(GameRound).filter(
                    GameRound.game_id == game_id,
                    GameRound.round_number == round_number,
                    GameRound.player_id == player.id
                ).first()
                if round_record and round_record.subsidy_verified == False:
                    caught_players.append({"player_id": player.id, "username": _player_display_name(player, db)})
                    round_results[player.id]["subsidy_result"] = "识破"
    
    # 一条广播包含两段内容，保证所有人看到相同
    await manager.broadcast_to_all_in_game({
        "type": "phase2_broadcasts",
        "applicants": subsidy_applicants,
        "caught_players": caught_players,
    }, game_id)
    
    await broadcast_round_results(game_id, round_results, 2, round_number)

async def process_phase3_subsidy_broadcast(game_id: int, round_number: int, choices: dict, db: Session):
    """处理Phase 3的补贴申请广播（投票前）"""
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    
    # 广播：谁申请了补贴
    subsidy_applicants = []
    for player in players:
        if player.id in choices and choices[player.id].get("apply_subsidy"):
            subsidy_applicants.append({"player_id": player.id, "username": _player_display_name(player, db)})
    
    if subsidy_applicants:
        await manager.broadcast_to_all_in_game({
            "type": "subsidy_applied",
            "message": "以下玩家申请了生态补贴：",
            "applicants": subsidy_applicants,
            "next_step": "voting"
        }, game_id)
    
    # 通知进入投票阶段
    await manager.broadcast_to_all_in_game({
        "type": "voting_start",
        "message": "请对申请补贴的玩家进行投票质疑",
        "applicants": subsidy_applicants,
        "vote_submitted_player_ids": []
    }, game_id)

async def process_voting_phase(game_id: int, db: Session):
    """处理投票阶段"""
    game = db.query(Game).filter(Game.id == game_id).first()
    round_number = game.current_round
    
    # 统计投票
    votes = db.query(GameVote).filter(
        GameVote.game_id == game_id,
        GameVote.round_number == round_number
    ).all()
    
    vote_counts = {}
    for vote in votes:
        if vote.target_id is None:  # 谁都不选不记入得票
            continue
        vote_counts[vote.target_id] = vote_counts.get(vote.target_id, 0) + 1
    
    # 找出得票最高者
    if vote_counts:
        max_votes = max(vote_counts.values())
        most_voted = [pid for pid, count in vote_counts.items() if count == max_votes]
        
        if most_voted:
            target_id = most_voted[0] if len(most_voted) == 1 else random.choice(most_voted)
            
            # 核查被投票者
            target_round = db.query(GameRound).filter(
                GameRound.game_id == game_id,
                GameRound.round_number == round_number,
                GameRound.player_id == target_id
            ).first()
            
            target_player = db.query(GamePlayer).filter(GamePlayer.id == target_id).first()
            username = _player_display_name(target_player, db)
            
            if target_round and target_round.choice == "inorganic" and target_round.applied_subsidy:
                # 被识破
                target_round.subsidy_verified = False
                base_earnings = calculate_earnings("inorganic", target_round.env_before)
                # 当前round_nt_earned = 基础收益 - 质押
                # 需要调整为：-质押（失去基础收益和质押）
                target_player.current_nt -= base_earnings  # 扣除基础收益
                target_round.round_nt_earned = -PHASE3_SUBSIDY  # 只扣除质押，无收益
                db.commit()
                
                # 投票者平分罚没的 2 NT 质押
                voters = [v.voter_id for v in votes if v.target_id == target_id]
                if voters:
                    reward_per_voter = PHASE3_SUBSIDY / len(voters)  # 共 2 NT 平分
                    for voter_id in voters:
                        voter_player = db.query(GamePlayer).filter(GamePlayer.id == voter_id).first()
                        if voter_player:
                            voter_player.current_nt += reward_per_voter
                    db.commit()
                
                vote_msg = {"type": "vote_result", "message": f"{username} 被投票质疑，核查后发现使用无机肥申请补贴，被识破！", "target_id": target_id, "caught": True}
                await manager.broadcast_to_all_in_game(vote_msg, game_id)
                phase3_round_broadcasts.setdefault((game_id, round_number), []).append(vote_msg)
            else:
                # 通过验证
                target_round.subsidy_verified = True
                db.commit()
                
                vote_msg = {"type": "vote_result", "message": f"{username} 被投票质疑，核查后确认使用有机肥，通过验证。", "target_id": target_id, "caught": False}
                await manager.broadcast_to_all_in_game(vote_msg, game_id)
                phase3_round_broadcasts.setdefault((game_id, round_number), []).append(vote_msg)
    
    # 处理50%概率识破和最终收益计算
    await process_phase3_final_calculation(game_id, round_number, db)

async def process_phase3_final_calculation(game_id: int, round_number: int, db: Session):
    """处理Phase 3的最终计算（50%概率识破和补贴收益）"""
    game = db.query(Game).filter(Game.id == game_id).first()
    choices = game_states[game_id]
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    
    caught_players = []
    for player in players:
        if player.id in choices:
            choice_data = choices[player.id]
            round_record = db.query(GameRound).filter(
                GameRound.game_id == game_id,
                GameRound.round_number == round_number,
                GameRound.player_id == player.id
            ).first()
            
            if not round_record:
                continue
            
            # 如果申请了补贴
            if round_record.applied_subsidy:
                # 如果还没被投票识破，检查50%概率
                if round_record.subsidy_verified is None:
                    is_caught = check_subsidy_verification(round_record.choice, 3, False)
                    round_record.subsidy_verified = is_caught
                    
                    if not is_caught:
                        # 被识破，质押已被扣除，还需要扣除本轮基础收益
                        base_earnings = calculate_earnings(round_record.choice, round_record.env_before)
                        player.current_nt -= base_earnings  # 扣除基础收益
                        round_record.round_nt_earned = -PHASE3_SUBSIDY  # 只扣除质押，无收益
                        caught_players.append({"player_id": player.id, "username": _player_display_name(player, db)})
                    else:
                        # 通过验证，返还质押并获得补贴
                        player.current_nt += PHASE3_SUBSIDY * 2
                        round_record.round_nt_earned += PHASE3_SUBSIDY * 2
                elif round_record.subsidy_verified == True:
                    # 通过验证，返还质押并获得补贴
                    player.current_nt += PHASE3_SUBSIDY * 2
                    round_record.round_nt_earned += PHASE3_SUBSIDY * 2
                # 如果subsidy_verified == False，说明被投票识破，已经处理过了
    
    db.commit()
    
    # 始终加入「系统识破」广播，无人识破时显示「没有」
    sys_caught_msg = {
        "type": "subsidy_caught",
        "message": "以下玩家使用无机肥但申请补贴被系统识破：",
        "caught_players": caught_players,
    }
    if caught_players:
        await manager.broadcast_to_all_in_game(sys_caught_msg, game_id)
    phase3_round_broadcasts.setdefault((game_id, round_number), []).append(sys_caught_msg)
    
    # 广播最终结果（携带本轮两条广播，供结果页同时展示）
    await broadcast_phase3_final_results(game_id, round_number, db)
    
    # Phase 3 也等待所有人点击「下一轮」再进入下一轮，保证同步
    ready_for_next_round_states[(game_id, round_number)] = set()
    # 不在此处调用 check_next_round_or_phase，由 handle_ready_for_next_round 在全员确认后调用

async def broadcast_phase3_final_results(game_id: int, round_number: int, db: Session):
    """广播Phase 3最终结果（含本轮投票结果 + 系统识破两条广播，供结果页同时展示）"""
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    round_results = {}
    phase3_broadcasts = phase3_round_broadcasts.pop((game_id, round_number), [])
    
    for player in players:
        round_record = db.query(GameRound).filter(
            GameRound.game_id == game_id,
            GameRound.round_number == round_number,
            GameRound.player_id == player.id
        ).first()
        
        if round_record:
            round_results[player.id] = {
                "nt_before": round_record.nt_before,
                "nt_after": player.current_nt,  # 可能被扣除
                "env_before": round_record.env_before,
                "env_after": player.current_env,
                "round_nt_earned": round_record.round_nt_earned,
                "env_change": get_env_change_text(player.current_env - round_record.env_before),
                "subsidy_result": "通过" if round_record.subsidy_verified else ("识破" if round_record.subsidy_verified == False else None),
                "phase3_broadcasts": phase3_broadcasts,
            }
    
    await broadcast_round_results(game_id, round_results, 3, round_number)

async def broadcast_round_results(game_id: int, round_results: dict, phase: int, round_number: int = None):
    """广播轮次结果给所有玩家"""
    db = SessionLocal()
    try:
        if round_number is None:
            game = db.query(Game).filter(Game.id == game_id).first()
            round_number = game.current_round if game else 0
    finally:
        db.close()
    
    for player_id, result in round_results.items():
        # Phase 1: 只显示NT和生态值变化
        if phase == 1:
            await manager.send_personal_message({
                "type": "round_result",
                "round_number": round_number,
                "phase": phase,
                "nt_after": result["nt_after"],
                "env_change": result["env_change"],
                "round_nt_earned": result["round_nt_earned"]
            }, game_id, player_id)
        else:
            # Phase 2和3: 显示完整信息；Phase 3 额外带 phase3_broadcasts 供结果页展示两条广播
            payload = {
                "type": "round_result",
                "round_number": round_number,
                "phase": phase,
                "nt_before": result["nt_before"],
                "nt_after": result["nt_after"],
                "env_before": result["env_before"],
                "env_after": result["env_after"],
                "round_nt_earned": result["round_nt_earned"],
                "subsidy_result": result.get("subsidy_result"),
            }
            if phase == 3 and result.get("phase3_broadcasts"):
                payload["phase3_broadcasts"] = result["phase3_broadcasts"]
            await manager.send_personal_message(payload, game_id, player_id)

async def check_next_round_or_phase(game_id: int, db: Session):
    """检查是否进入下一轮或下一阶段"""
    game = db.query(Game).filter(Game.id == game_id).first()
    
    # 清空当前轮次的选择
    if game_id in game_states:
        game_states[game_id] = {}
    
    # 判断下一阶段
    if game.current_round == 5:
        game.phase = 2
    elif game.current_round == 10:
        game.phase = 3
    elif game.current_round == 15:
        # 游戏结束
        await finish_game(game_id, db)
        return
    
    # 进入下一轮
    game.current_round += 1
    db.commit()
    
    # 附带最新玩家数据供前端同步
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    players_data = []
    for p in players:
        players_data.append({
            "id": p.id,
            "user_id": getattr(p, "user_id", None),
            "username": _player_display_name(p, db),
            "current_nt": p.current_nt,
            "current_env": p.current_env
        })
    
    await manager.broadcast_to_all_in_game({
        "type": "next_round",
        "message": f"进入第 {game.current_round} 轮",
        "current_round": game.current_round,
        "phase": game.phase,
        "players": players_data,
        "submitted_player_ids": []
    }, game_id)

async def finish_game(game_id: int, db: Session):
    """结束游戏并结算"""
    game = db.query(Game).filter(Game.id == game_id).first()
    game.status = "finished"
    game.finished_at = datetime.utcnow()
    
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    
    # 最终结算
    max_env = max([p.current_env for p in players])
    for player in players:
        # 生态值转换为NT
        player.final_nt = final_settlement(player.current_nt, player.current_env)
        player.final_env = player.current_env
        
        # 标记获胜者
        if player.current_env == max_env:
            player.is_winner = True
    
    db.commit()
    
    # 导出Excel
    try:
        excel_path = export_game_to_excel(db, game_id)
    except Exception as e:
        print(f"导出Excel失败: {e}")
        excel_path = None
    
    # 广播游戏结束
    await manager.broadcast_to_all_in_game({
        "type": "game_finished",
        "message": "游戏结束！",
        "excel_path": excel_path
    }, game_id)

@app.get("/api/games/{game_id}/excel")
async def download_excel(game_id: int, db: Session = Depends(get_db)):
    """下载游戏Excel数据"""
    try:
        excel_path = export_game_to_excel(db, game_id)
        return FileResponse(excel_path, filename=f"game_{game_id}_data.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
