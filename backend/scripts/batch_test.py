"""
批量随机测试：10 局游戏，每局 20–30 人，行为完全随机。
用于观察当前数值设计是否能拉开玩家差距。
每局结果导出到同一 Excel，每局一页（游戏1 … 游戏10）。

测试数据只存在于内存数据库，不写入真实 game.db，仅生成 Excel 文件。
"""
import random
import os
import sys
from datetime import datetime

# 保证能导入 app（从 backend 目录运行）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.models import (
    Base,
    Game, GamePlayer, GameRound, GameVote,
)
from app.game_logic import (
    INITIAL_NT, INITIAL_ENV,
    calculate_earnings, calculate_env_change, check_subsidy_verification,
    final_settlement, get_env_change_text,
    PHASE2_SUBSIDY, PHASE3_SUBSIDY,
)
from app.excel_export import export_batch_to_excel


def _player_display_name(player, db: Session) -> str:
    if getattr(player, "username", None) and str(player.username).strip():
        return (player.username or "").strip()
    return f"玩家{player.id}"


def run_one_round_sync(db: Session, game_id: int, round_number: int, phase: int, choices: dict) -> None:
    """同步执行一轮：收益、生态值、补贴验证（Phase2 立即，Phase3 投票后另算），写 GameRound、更新玩家。"""
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    all_choices = {pid: choices[pid]["choice"] for pid in choices}

    for player in players:
        if player.id not in choices:
            continue
        c = choices[player.id]
        choice = c["choice"]
        apply_subsidy = c.get("apply_subsidy", False)
        env_change = calculate_env_change(choice, player.id, all_choices)
        earnings = calculate_earnings(choice, player.current_env)
        subsidy_verified = None
        if apply_subsidy and phase >= 2:
            amt = PHASE2_SUBSIDY if phase == 2 else PHASE3_SUBSIDY
            earnings -= amt
            if phase == 2:
                subsidy_verified = check_subsidy_verification(choice, phase)
                if subsidy_verified:
                    earnings += amt * 2
            # Phase 3 补贴在投票+系统识破后再算，这里只扣质押

        nt_before = player.current_nt
        env_before = player.current_env
        player.current_nt += earnings
        player.current_env += env_change
        round_record = GameRound(
            game_id=game_id,
            round_number=round_number,
            phase=phase,
            player_id=player.id,
            choice=choice,
            applied_subsidy=apply_subsidy,
            subsidy_verified=subsidy_verified,
            nt_before=nt_before,
            nt_after=player.current_nt,
            env_before=env_before,
            env_after=player.current_env,
            round_nt_earned=earnings,
        )
        db.add(round_record)
    db.commit()


def run_phase2_caught_sync(db: Session, game_id: int, round_number: int, choices: dict) -> None:
    """Phase 2：标记被识破者（无机肥+申领且 subsidy_verified==False 已在 run_one_round 里设好）。"""
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    for player in players:
        if player.id not in choices or not choices[player.id].get("apply_subsidy") or choices[player.id].get("choice") != "inorganic":
            continue
        r = db.query(GameRound).filter(
            GameRound.game_id == game_id,
            GameRound.round_number == round_number,
            GameRound.player_id == player.id,
        ).first()
        if r and r.subsidy_verified is False:
            pass  # 已在上一步设好
    db.commit()


def run_phase3_voting_and_final_sync(db: Session, game_id: int, round_number: int, choices: dict) -> None:
    """Phase 3：模拟随机投票，然后处理投票识破 + 50% 系统识破 + 补贴结算。"""
    from app.game_logic import PHASE3_SUBSIDY
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    applicants = [p for p in players if p.id in choices and choices[p.id].get("apply_subsidy")]
    # 每人随机：投给一名申请者 或 谁都不选（target_id=None，Excel 记 0）
    options = [None] + [a.id for a in applicants]
    for p in players:
        target_id = random.choice(options)
        v = GameVote(game_id=game_id, round_number=round_number, voter_id=p.id, target_id=target_id)
        db.add(v)
    db.commit()

    votes = db.query(GameVote).filter(
        GameVote.game_id == game_id,
        GameVote.round_number == round_number,
    ).all()
    vote_counts = {}
    for v in votes:
        if v.target_id is None:
            continue
        vote_counts[v.target_id] = vote_counts.get(v.target_id, 0) + 1
    if vote_counts:
        max_v = max(vote_counts.values())
        most = [tid for tid, c in vote_counts.items() if c == max_v]
        target_id = most[0] if len(most) == 1 else random.choice(most)
        target_round = db.query(GameRound).filter(
            GameRound.game_id == game_id,
            GameRound.round_number == round_number,
            GameRound.player_id == target_id,
        ).first()
        target_player = db.query(GamePlayer).filter(GamePlayer.id == target_id).first()
        if target_round and target_round.choice == "inorganic" and target_round.applied_subsidy:
            target_round.subsidy_verified = False
            base_earnings = calculate_earnings("inorganic", target_round.env_before)
            target_player.current_nt -= base_earnings
            target_round.round_nt_earned = -PHASE3_SUBSIDY
            voters = [v.voter_id for v in votes if v.target_id == target_id]
            if voters:
                reward_per = PHASE3_SUBSIDY / len(voters)
                for vid in voters:
                    vp = db.query(GamePlayer).filter(GamePlayer.id == vid).first()
                    if vp:
                        vp.current_nt += reward_per
        else:
            target_round.subsidy_verified = True
        db.commit()

    # 50% 系统识破 + 补贴结算
    for player in players:
        if player.id not in choices:
            continue
        r = db.query(GameRound).filter(
            GameRound.game_id == game_id,
            GameRound.round_number == round_number,
            GameRound.player_id == player.id,
        ).first()
        if not r or not r.applied_subsidy:
            continue
        if r.subsidy_verified is None:
            is_caught = check_subsidy_verification(r.choice, 3, False)
            r.subsidy_verified = is_caught
            if not is_caught:  # 被识破
                base_earnings = calculate_earnings(r.choice, r.env_before)
                player.current_nt -= base_earnings
                r.round_nt_earned = -PHASE3_SUBSIDY
            else:
                player.current_nt += PHASE3_SUBSIDY * 2
                r.round_nt_earned += PHASE3_SUBSIDY * 2
        elif r.subsidy_verified is True:
            player.current_nt += PHASE3_SUBSIDY * 2
            r.round_nt_earned += PHASE3_SUBSIDY * 2
    db.commit()


def check_next_round_sync(db: Session, game_id: int) -> bool:
    """进入下一轮/下一阶段；若游戏结束返回 True。"""
    game = db.query(Game).filter(Game.id == game_id).first()
    if game.current_round == 5:
        game.phase = 2
    elif game.current_round == 10:
        game.phase = 3
    elif game.current_round == 15:
        return True  # 结束
    game.current_round += 1
    db.commit()
    return False


def finish_game_sync(db: Session, game_id: int) -> None:
    """结束游戏并结算 final_nt / final_env / is_winner。"""
    game = db.query(Game).filter(Game.id == game_id).first()
    game.status = "finished"
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    max_env = max(p.current_env for p in players)
    for p in players:
        p.final_nt = final_settlement(p.current_nt, p.current_env)
        p.final_env = p.current_env
        p.is_winner = p.current_env == max_env
    db.commit()


def create_game_and_players(db: Session, num_players: int) -> int:
    """创建一局游戏和 num_players 个玩家，返回 game_id。"""
    game = Game(
        game_code="".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6)),
        status="playing",
        creator_id=None,
        current_round=1,
        phase=1,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    for i in range(num_players):
        p = GamePlayer(
            game_id=game.id,
            user_id=None,
            username=f"测试玩家{i+1}",
            initial_nt=INITIAL_NT,
            current_nt=INITIAL_NT,
            current_env=INITIAL_ENV,
        )
        db.add(p)
    db.commit()
    db.refresh(game)
    game.creator_id = db.query(GamePlayer).filter(GamePlayer.game_id == game.id).first().id
    db.commit()
    return game.id


def run_one_game(db: Session, num_players: int) -> int:
    """跑完一局 15 轮，全员随机选择；返回 game_id。"""
    game_id = create_game_and_players(db, num_players)
    players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    player_ids = [p.id for p in players]

    for round_number in range(1, 16):
        phase = 1 if round_number <= 5 else (2 if round_number <= 10 else 3)
        choices = {}
        for pid in player_ids:
            choices[pid] = {
                "choice": random.choice(["organic", "inorganic"]),
                "apply_subsidy": random.choice([True, False]) if phase >= 2 else False,
            }
        run_one_round_sync(db, game_id, round_number, phase, choices)
        if phase == 2:
            run_phase2_caught_sync(db, game_id, round_number, choices)
        elif phase == 3:
            run_phase3_voting_and_final_sync(db, game_id, round_number, choices)
        if check_next_round_sync(db, game_id):
            break
    finish_game_sync(db, game_id)
    return game_id


def main():
    # 使用内存 SQLite，不写入真实数据库，测试数据仅用于生成 Excel
    memory_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=memory_engine)
    SessionLocalMemory = sessionmaker(autocommit=False, autoflush=False, bind=memory_engine)
    db = SessionLocalMemory()
    num_games = 10
    min_players, max_players = 20, 30
    game_ids = []
    try:
        for i in range(num_games):
            n = random.randint(min_players, max_players)
            gid = run_one_game(db, n)
            game_ids.append(gid)
            print(f"  完成第 {i+1}/{num_games} 局：game_id={gid}，玩家数={n}")
        out_dir = "exports"
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, f"batch_test_10games_{stamp}.xlsx")
        export_batch_to_excel(db, game_ids, out_path)
        print(f"  已导出: {os.path.abspath(out_path)}")
    finally:
        db.close()
    print("批量测试完成。")


if __name__ == "__main__":
    main()
