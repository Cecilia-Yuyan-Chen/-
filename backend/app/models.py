from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    questionnaire_answers = Column(Text, nullable=True)  # Q1–Q12 问卷答案（JSON 字符串）
    created_at = Column(DateTime, default=datetime.utcnow)

class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    game_code = Column(String, unique=True, index=True)
    creator_id = Column(Integer, nullable=True)  # 房间创建者的 GamePlayer.id，非 User.id
    status = Column(String, default="waiting")  # waiting, playing, finished
    current_round = Column(Integer, default=0)
    phase = Column(Integer, default=1)  # 1, 2, 3
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    
    players = relationship("GamePlayer", back_populates="game")
    rounds = relationship("GameRound", back_populates="game")

class GamePlayer(Base):
    __tablename__ = "game_players"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 兼容旧数据，新流程不用
    username = Column(String, nullable=True)  # 本局昵称，不持久化到用户表
    initial_nt = Column(Float, default=10.0)
    current_nt = Column(Float, default=10.0)
    current_env = Column(Float, default=0.0)
    final_nt = Column(Float, nullable=True)
    final_env = Column(Float, nullable=True)
    is_winner = Column(Boolean, default=False)
    
    game = relationship("Game", back_populates="players")
    user = relationship("User")
    rounds = relationship("GameRound", back_populates="player")

class GameRound(Base):
    __tablename__ = "game_rounds"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    round_number = Column(Integer, nullable=False)
    phase = Column(Integer, nullable=False)  # 1, 2, 3
    player_id = Column(Integer, ForeignKey("game_players.id"))
    choice = Column(String, nullable=False)  # organic, inorganic
    applied_subsidy = Column(Boolean, default=False)
    subsidy_verified = Column(Boolean, nullable=True)  # True=通过, False=识破, None=未申请
    votes_received = Column(Integer, default=0)
    nt_before = Column(Float, nullable=False)
    nt_after = Column(Float, nullable=False)
    env_before = Column(Float, nullable=False)
    env_after = Column(Float, nullable=False)
    round_nt_earned = Column(Float, nullable=False)
    
    game = relationship("Game", back_populates="rounds")
    player = relationship("GamePlayer", back_populates="rounds")

class GameVote(Base):
    __tablename__ = "game_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    round_number = Column(Integer, nullable=False)
    voter_id = Column(Integer, ForeignKey("game_players.id"))
    target_id = Column(Integer, ForeignKey("game_players.id"), nullable=True)  # None = 谁都不选，Excel 记 0

# 数据库初始化
DATABASE_URL = "sqlite:///./game.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # 兼容旧库：按需添加列
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE games ADD COLUMN creator_id INTEGER",
            "ALTER TABLE game_players ADD COLUMN username TEXT",
            "ALTER TABLE users ADD COLUMN questionnaire_answers TEXT",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()
                pass
