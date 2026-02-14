import React, { useState, useEffect, useMemo } from 'react'
import { api } from '../services/api'

function Lobby({ user, player, game, gameState, onCreateGame, onJoinGame, onStartGame, onLoadGameState }) {
  const [gameCode, setGameCode] = useState('')
  const [players, setPlayers] = useState([])

  // 去重：同一 user_id 或同一 id 只显示一条（防止重复加入导致列表重复）
  const uniquePlayers = useMemo(() => {
    const seen = new Set()
    return players.filter((p) => {
      const key = p.user_id != null ? `u${p.user_id}` : `p${p.id}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [players])

  useEffect(() => {
    if (game) {
      loadPlayers()
      const interval = setInterval(loadPlayers, 2000)
      return () => clearInterval(interval)
    }
  }, [game])

  const loadPlayers = async () => {
    if (game) {
      try {
        const response = await api.get(`/games/${game.id}/players`)
        setPlayers(response.data)
      } catch (error) {
        console.error('加载玩家列表失败:', error)
      }
    }
  }

  const handleJoinByCode = async () => {
    const code = gameCode.trim()
    if (!code) {
      alert('请输入游戏房间号')
      return
    }
    try {
      // 支持 6 位字母数字房间号（如 ABC123）或数字 ID
      const asNumber = parseInt(code, 10)
      if (!isNaN(asNumber) && String(asNumber) === code) {
        await onJoinGame(asNumber)
      } else {
        // 按房间号查询
        const res = await api.get(`/games/by-code/${encodeURIComponent(code.toUpperCase())}`)
        await onJoinGame(res.data.id)
      }
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || '加入失败'
      alert(typeof msg === 'string' ? msg : '房间号不存在或已失效，请检查后重试')
    }
  }

  return (
    <div className="container">
      <h1>游戏大厅</h1>
      <div className="card">
        <p>欢迎，<strong>{user?.username || '玩家'}</strong>！</p>
      </div>

      {!game ? (
        <>
          <button onClick={onCreateGame} style={{ width: '100%', marginTop: '20px' }}>
            创建新游戏
          </button>
          <div style={{ marginTop: 'px', textAlign: 'center' }}>
            <input
              type="text"
              placeholder="输入 6 位房间号（如 ABC123）或数字 ID"
              value={gameCode}
              onChange={(e) => setGameCode(e.target.value)}
              maxLength={20}
            />
            <button onClick={handleJoinByCode} style={{ width: '100%' }}>
              加入游戏
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="card">
            <h3>游戏房间</h3>
            <p className="room-code">房间号：<strong>{game.game_code || game.id}</strong></p>
            <p className="room-code-hint">将上方房间号发给其他人，对方在下方输入后点击「加入游戏」即可</p>
            <p>当前玩家数：{uniquePlayers.length} / 99</p>
          </div>

          <div className="card">
            <h3>玩家列表</h3>
            {uniquePlayers.length === 0 ? (
              <p>暂无玩家</p>
            ) : (
              <ul>
                {uniquePlayers.map((p) => (
                  <li key={p.id}>{p.username}</li>
                ))}
              </ul>
            )}
          </div>

          {uniquePlayers.length >= 2 && (game.creator_id == null || game.creator_id === player?.id) && (
            <button onClick={onStartGame} style={{ width: '100%', marginTop: '20px' }}>
              开始游戏{game.creator_id != null ? '（仅房主）' : ''}
            </button>
          )}
          {uniquePlayers.length >= 2 && game.creator_id != null && game.creator_id !== player?.id && (
            <p className="waiting-hint">等待房主开始游戏…</p>
          )}
        </>
      )}
    </div>
  )
}

export default Lobby
