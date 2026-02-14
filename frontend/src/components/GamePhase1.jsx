import React, { useState, useEffect } from 'react'
import { sendMessage } from '../services/websocket'
import PhaseRoundHeader from './PhaseRoundHeader'

function GamePhase1({ game, player, gameState, ws }) {
  const [selectedChoice, setSelectedChoice] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [roundResult, setRoundResult] = useState(null)
  const [currentPlayer, setCurrentPlayer] = useState(null)

  useEffect(() => {
    if (gameState?.players) {
      const p = gameState.players.find(p => p.id === player.id)
      setCurrentPlayer(p)
    }
  }, [gameState, player])

  useEffect(() => {
    setRoundResult(gameState?.round_result ?? null)
    if (gameState?.round_result) {
      setSubmitted(false)
      setSelectedChoice(null)
    }
  }, [gameState])

  const handleSubmit = () => {
    if (selectedChoice && ws) {
      sendMessage(ws, 'submit_choice', {
        choice: selectedChoice,
        apply_subsidy: false
      })
      setSubmitted(true)
    }
  }

  if (roundResult) {
    return (
      <div className="container">
        <PhaseRoundHeader phase={roundResult.phase || 1} round={roundResult.round_number} />
        <h1>第 {roundResult.round_number} 轮结果</h1>
        <div className="card">
          <div className="stats">
            <div className="stat-item">
              <div className="stat-value">{roundResult.nt_after.toFixed(1)}</div>
              <div className="stat-label">当前NT</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{roundResult.env_change}</div>
              <div className="stat-label">生态值变化</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">+{roundResult.round_nt_earned.toFixed(1)}</div>
              <div className="stat-label">本轮收益</div>
            </div>
          </div>
        </div>
        <p style={{ textAlign: 'center', marginTop: '20px' }}>
          等待下一轮开始...
        </p>
      </div>
    )
  }

  return (
    <div className="container">
      <PhaseRoundHeader phase={gameState?.phase || 1} round={gameState?.current_round || 1} />
      <h1>🌫️ 迷雾村庄</h1>
      
      {currentPlayer && (
        <div className="card">
          <div className="stats">
            <div className="stat-item">
              <div className="stat-value">{currentPlayer.current_nt.toFixed(1)}</div>
              <div className="stat-label">当前NT</div>
            </div>
          </div>
          <p style={{ textAlign: 'center', marginTop: '10px', color: '#666' }}>
            注意：在迷雾村庄阶段，你无法看到自己的生态值数值，只能看到变化趋势
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
              <small>获得3NT，自己生态值+1，其他所有人生态值+0.5</small>
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
              <small>获得6NT，自己生态值-1，其他所有人生态值-0.5</small>
            </button>
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

export default GamePhase1
