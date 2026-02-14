import React, { useState, useEffect } from 'react'
import { sendMessage } from '../services/websocket'
import PhaseRoundHeader from './PhaseRoundHeader'

function GamePhase3({ game, player, gameState, ws }) {
  const [selectedChoice, setSelectedChoice] = useState(null)
  const [applySubsidy, setApplySubsidy] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [roundResult, setRoundResult] = useState(null)
  const [currentPlayer, setCurrentPlayer] = useState(null)
  const [broadcast, setBroadcast] = useState(null)
  const [votingPhase, setVotingPhase] = useState(false)
  const [votingApplicants, setVotingApplicants] = useState([])
  const [selectedVote, setSelectedVote] = useState(null)
  const [voteSubmitted, setVoteSubmitted] = useState(false)
  const [readyClicked, setReadyClicked] = useState(false)

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
      setApplySubsidy(false)
      setVotingPhase(false)
      setVoteSubmitted(false)
      setReadyClicked(false)
    }
    if (gameState?.broadcast) {
      setBroadcast(gameState.broadcast)
    }
    if (gameState?.voting_phase) {
      setVotingPhase(true)
      setVotingApplicants(gameState.voting_applicants || [])
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

  const handleVote = (overrideTargetId) => {
    const tid = overrideTargetId !== undefined ? overrideTargetId : selectedVote
    if (ws && (tid === 0 || tid)) {
      sendMessage(ws, 'submit_vote', {
        target_id: tid === 0 ? 0 : tid
      })
      setVoteSubmitted(true)
    }
  }

  const handleReadyNextRound = () => {
    if (ws) {
      sendMessage(ws, 'ready_for_next_round', {})
      setReadyClicked(true)
    }
  }

  const baseEarnings = (choice) => (choice === 'organic' ? 3 : 6)

  if (roundResult) {
    const broadcasts = roundResult.phase3_broadcasts && roundResult.phase3_broadcasts.length > 0
      ? roundResult.phase3_broadcasts
      : (broadcast ? [broadcast] : [])

    return (
      <div className="container">
        <PhaseRoundHeader phase={roundResult.phase || 3} round={roundResult.round_number} />
        <h1>第 {roundResult.round_number} 轮结果</h1>
        
        {broadcasts.map((b, idx) => (
          <div
            key={idx}
            className={`broadcast ${
              b.type === 'subsidy_caught' || (b.type === 'vote_result' && b.caught)
                ? 'error'
                : b.type === 'vote_result' && !b.caught
                  ? 'success'
                  : ''
            }`}
          >
            <strong>{b.message}</strong>
            {b.applicants && (
              b.applicants.length > 0 ? (
                <ul style={{ marginTop: '10px' }}>
                  {b.applicants.map((a, i) => (
                    <li key={i}>{a.username}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ marginTop: '10px', color: '#666' }}>没有</p>
              )
            )}
            {b.type === 'subsidy_caught' && (
              (b.caught_players && b.caught_players.length > 0) ? (
                <ul style={{ marginTop: '10px' }}>
                  {b.caught_players.map((p, i) => (
                    <li key={i}>{p.username}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ marginTop: '10px', color: '#666' }}>没有</p>
              )
            )}
          </div>
        ))}

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

  if (votingPhase && !voteSubmitted) {
    return (
      <div className="container">
        <PhaseRoundHeader phase={3} round={gameState?.current_round || 11} />
        <h1>🗳️ 投票质疑阶段</h1>
        
        <div className="card">
          <p style={{ marginBottom: '15px' }}>
            请对申请生态补贴的玩家进行投票质疑。得票最高的玩家将被核查。
          </p>
          {votingApplicants.length === 0 ? (
            <>
              <p style={{ marginBottom: '15px' }}>没有玩家申请补贴，请确认后进入下一轮。</p>
              <button
                onClick={() => handleVote(0)}
                style={{ width: '100%', marginTop: '10px' }}
              >
                确认（无人申请补贴）
              </button>
            </>
          ) : (
            <>
              <button
                className={`vote-button${selectedVote === 0 ? ' selected' : ''}`}
                onClick={() => setSelectedVote(0)}
                style={{
                  backgroundColor: selectedVote === 0 ? '#9e9e9e' : '#e0e0e0',
                  color: selectedVote === 0 ? 'white' : 'black',
                  marginBottom: '8px'
                }}
              >
                谁都不选
              </button>
              {votingApplicants.map((applicant) => (
                <button
                  key={applicant.player_id}
                  className={`vote-button${selectedVote === applicant.player_id ? ' selected' : ''}`}
                  onClick={() => setSelectedVote(applicant.player_id)}
                  style={{
                    backgroundColor: selectedVote === applicant.player_id ? '#667eea' : '#e0e0e0',
                    color: selectedVote === applicant.player_id ? 'white' : 'black'
                  }}
                >
                  {applicant.username}
                </button>
              ))}
              <button
                onClick={() => handleVote()}
                disabled={selectedVote === undefined || selectedVote === null}
                style={{ width: '100%', marginTop: '20px' }}
              >
                提交投票
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  if (votingPhase && voteSubmitted) {
    return (
      <div className="container">
        <PhaseRoundHeader phase={3} round={gameState?.current_round || 11} />
        <h1>🗳️ 投票质疑阶段</h1>
        <div className="card">
          <p style={{ textAlign: 'center', fontSize: '18px' }}>
            已提交投票，等待其他玩家…
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <PhaseRoundHeader phase={3} round={gameState?.current_round || 11} />
      <h1>👥 数字村民</h1>
      
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
          <p style={{ textAlign: 'center', marginTop: '10px', color: '#dc3545', fontWeight: 'bold' }}>
            注意：识破概率已大幅提高！
          </p>
        </div>
      )}

      {broadcast && (
        <div className={`broadcast ${broadcast.type === 'subsidy_caught' ? 'error' : ''}`}>
          <strong>{broadcast.message}</strong>
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
              <small>本轮收益：{baseEarnings('organic')}NT</small>
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
              <small>本轮收益：{baseEarnings('inorganic')}NT</small>
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
              <span>申请生态补贴（2NT，需质押2NT）</span>
            </label>
            <p style={{ marginTop: '10px', color: '#dc3545', fontSize: '14px', fontWeight: 'bold' }}>
              警告：使用无机肥申请补贴有大概率被识破，识破后将扣除质押NT且本轮无收益！
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

export default GamePhase3
