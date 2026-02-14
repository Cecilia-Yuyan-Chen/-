import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

function Results({ game, player }) {
  const [results, setResults] = useState(null)

  useEffect(() => {
    loadResults()
  }, [game])

  const loadResults = async () => {
    try {
      const players = await api.get(`/games/${game.id}/players`)
      setResults(players.data)
    } catch (error) {
      console.error('加载结果失败:', error)
    }
  }

  const downloadExcel = async () => {
    try {
      // 获取API基础URL
      const apiBaseURL = api.defaults.baseURL || '/api'
      window.open(`${apiBaseURL}/games/${game.id}/excel`, '_blank')
    } catch (error) {
      console.error('下载Excel失败:', error)
      alert('下载失败，请重试')
    }
  }

  if (!results) {
    return <div className="loading">加载结果中...</div>
  }

  // 找出生态值最高的玩家
  const maxEnv = Math.max(...results.map(p => p.final_env || p.current_env))
  const winner = results.find(p => (p.final_env || p.current_env) === maxEnv)

  return (
    <div className="container">
      <h1>🎉 游戏结束</h1>
      
      <div className="card">
        <h2>🏆 南塘生态大王</h2>
        {winner && (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#667eea' }}>
              {winner.username}
            </div>
            <div style={{ marginTop: '10px', color: '#666' }}>
              生态值: {winner.final_env || winner.current_env}
            </div>
            <div style={{ marginTop: '10px', fontSize: '1.2em' }}>
              🎁 获得"南塘生态大王"NFT空投
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h2>最终排名</h2>
        <p style={{ marginBottom: '12px', color: '#666', fontSize: '0.9rem' }}>
          15 轮结束后，生态值在此时一次性折算为 NT：正生态每 1 点 = +0.5 NT，负生态每 -1 点 = -1 NT。
        </p>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
              <th style={{ padding: '10px', textAlign: 'left' }}>排名</th>
              <th style={{ padding: '10px', textAlign: 'left' }}>玩家</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>NT(结算前)</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>生态值</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>生态结算</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>最终NT</th>
            </tr>
          </thead>
          <tbody>
            {results
              .sort((a, b) => (b.final_nt ?? b.current_nt ?? 0) - (a.final_nt ?? a.current_nt ?? 0))
              .map((p, index) => {
                const ntBefore = p.nt_before_settlement ?? p.current_nt
                const envVal = p.final_env ?? p.current_env ?? 0
                const envSettle = p.env_settlement ?? 0
                const finalNt = p.final_nt ?? p.current_nt
                return (
                  <tr key={p.id} style={{ borderBottom: '1px solid #e0e0e0' }}>
                    <td style={{ padding: '10px' }}>{index + 1}</td>
                    <td style={{ padding: '10px' }}>
                      {p.username}
                      {p.id === player.id && <span style={{ color: '#667eea' }}> (你)</span>}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>{Number(ntBefore).toFixed(1)}</td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>{Number(envVal).toFixed(1)}</td>
                    <td style={{ padding: '10px', textAlign: 'right', color: envSettle >= 0 ? '#28a745' : '#dc3545' }}>
                      {envSettle >= 0 ? '+' : ''}{Number(envSettle).toFixed(1)}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>{Number(finalNt).toFixed(1)}</td>
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>

      <button onClick={downloadExcel} style={{ width: '100%', marginTop: '20px' }}>
        下载Excel数据表格
      </button>
    </div>
  )
}

export default Results
