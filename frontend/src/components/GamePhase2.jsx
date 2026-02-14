import React, { useState, useEffect } from 'react'
import { sendMessage } from '../services/websocket'
import PhaseRoundHeader from './PhaseRoundHeader'

function GamePhase2({ game, player, gameState, ws }) {
  const [selectedChoice, setSelectedChoice] = useState(null)
  const [applySubsidy, setApplySubsidy] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [roundResult, setRoundResult] = useState(null)
  const [currentPlayer, setCurrentPlayer] = useState(null)
  const [phase2Broadcasts, setPhase2Broadcasts] = useState(null)
  const [readyClicked, setReadyClicked] = useState(false)

  useEffect(() => {
    if (gameState?.players) {
      const p = gameState.players.find(p => p.id === player.id)
      setCurrentPlayer(p)
    }
  }, [gameState, player])

  useEffect(() => {
    setRoundResult(gameState?.round_result ?? null)
    setPhase2Broadcasts(gameState?.phase2_broadcasts ?? null)
    if (gameState?.round_result) {
      setSubmitted(false)
      setSelectedChoice(null)
      setApplySubsidy(false)
      setReadyClicked(false)
    }
  }, [gameState])

  const handleSubmit = () => {
    if (selectedChoice && ws) {
      sendMessage(ws, 'submit_choice', {
        choice: selectedChoice,
        apply_subsidy: applySubsidy
      })
      setSubmitted(true)
    }
  }

  const handleReadyNextRound = () => {
    if (ws) {
      sendMessage(ws, 'ready_for_next_round', {})
      setReadyClicked(true)
    }
  }

  // 游戏过程中 ENV 不参与 NT，仅基础收益
  const baseEarnings = (choice) => (choice === 'organic' ? 3 : 6)

  if (roundResult) {
    const broadcasts = phase2Broadcasts || {}
    const applicants = broadcasts.applicants || []
    const caught = broadcasts.caught_players || []
    return (
      <div className="container">
        <PhaseRoundHeader phase={roundResult.phase || 2} round={roundResult.round_number} />
        <h1>第 {roundResult.round_number} 轮结果</h1>

        <div className="broadcast">
          <strong>以下玩家申请了生态补贴：</strong>
          {applicants.length > 0 ? (
            <ul style={{ marginTop: '10px' }}>
              {applicants.map((a, i) => (
                <li key={i}>{a.username}</li>
              ))}
            </ul>
          ) : (
            <p style={{ marginTop: '10px', color: '#666' }}>没有</p>
          )}
        </div>
        <div className={`broadcast ${caught.length > 0 ? 'error' : ''}`}>
          <strong>以下玩家使用无机肥但申请补贴被识破：</strong>
          {caught.length > 0 ? (
            <ul style={{ marginTop: '10px' }}>
              {caught.map((p, i) => (
                <li key={i}>{p.username}</li>
              ))}
            </ul>
          ) : (
            <p style={{ marginTop: '10px', color: '#666' }}>没有</p>
          )}
        </div>

        <div className="card">
          <div className="stats">
            <div className="stat-item">
              <div className="stat-value">{roundResult.nt_after.toFixed(1)}</div>
              <div className="stat-label">当前NT</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{roundResult.env_after.toFixed(1)}</div>
              <div className="stat-label">当前生态值</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{roundResult.round_nt_earned >= 0 ? '+' : ''}{roundResult.round_nt_earned.toFixed(1)}</div>
              <div className="stat-label">本轮收益</div>
            </div>
          </div>
          {roundResult.subsidy_result && (
            <p style={{ textAlign: 'center', marginTop: '10px', color: roundResult.subsidy_result === '识破' ? '#dc3545' : '#28a745' }}>
              补贴验证：{roundResult.subsidy_result}
            </p>
          )}
        </div>

        {!readyClicked ? (
          <button onClick={handleReadyNextRound} style={{ width: '100%', marginTop: '20px' }}>
            下一轮
          </button>
        ) : (
          <p style={{ textAlign: 'center', marginTop: '20px', color: '#666' }}>
            已确认，等待其他玩家点击「下一轮」…
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="container">
      <PhaseRoundHeader phase={gameState?.phase || 2} round={gameState?.current_round || 6} />
      <h1>📖 公共账本</h1>
      
      {currentPlayer && (
        <div className="card">
          <div className="stats">
            <div className="stat-item">
              <div className="stat-value">{currentPlayer.current_nt.toFixed(1)}</div>
              <div className="stat-label">当前NT</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{currentPlayer.current_env.toFixed(1)}</div>
              <div className="stat-label">当前生态值</div>
            </div>
          </div>
          <p style={{ textAlign: 'center', marginTop: '10px', color: '#666' }}>
            生态值影响：每10点生态值 = +0.5NT基础收益
          </p>
        </div>
      )}

      {!submitted ? (
        <>
          <div className="card">
            <h3>请选择使用的肥料类型：</h3>
            <button
              className={`choice-button organic${selectedChoice === 'organic' ? ' selected' : ''}`}
              onClick={() => setSelectedChoice('organic')}
              style={{
                backgroundColor: selectedChoice === 'organic' ? '#38ef7d' : '#e0e0e0'
              }}
            >
              <strong>选项A：有机肥</strong>
              <br />
              <small>基础收益：3NT（受生态值影响）</small>
              <br />
              <small>本轮收益：{baseEarnings('organic')}NT（ENV 仅在全部15轮结束后折算）</small>
            </button>
            <button
              className={`choice-button inorganic${selectedChoice === 'inorganic' ? ' selected' : ''}`}
              onClick={() => setSelectedChoice('inorganic')}
              style={{
                backgroundColor: selectedChoice === 'inorganic' ? '#f45c43' : '#e0e0e0'
              }}
            >
              <strong>选项B：无机肥</strong>
              <br />
              <small>基础收益：6NT（受生态值影响）</small>
              <br />
              <small>本轮收益：{baseEarnings('inorganic')}NT（ENV 仅在全部15轮结束后折算）</small>
            </button>
          </div>

          <div className="card">
            <h3>生态补贴申请</h3>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={applySubsidy}
                onChange={(e) => setApplySubsidy(e.target.checked)}
                style={{ width: '20px', height: '20px', marginRight: '10px' }}
              />
              <span>申请生态补贴（1.5NT，需质押1.5NT）</span>
            </label>
            <p style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
              注意：使用无机肥申请补贴有一定概率被识破，识破后将扣除质押NT
            </p>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!selectedChoice}
            style={{ width: '100%', marginTop: '20px' }}
          >
            确认选择
          </button>
        </>
      ) : (
        <div className="card">
          <p style={{ textAlign: 'center', fontSize: '18px' }}>
            已提交选择，等待其他玩家...
          </p>
        </div>
      )}
    </div>
  )
}

export default GamePhase2
