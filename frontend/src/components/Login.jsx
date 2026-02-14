import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

const STORAGE_KEY = 'game_username'

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const saved = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem(STORAGE_KEY) : null
    if (saved) setUsername(saved)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const name = username.trim()
    if (!name) return
    setLoading(true)
    try {
      const res = await api.post('users/register', { username: name })
      const user = res.data
      if (typeof sessionStorage !== 'undefined') sessionStorage.setItem(STORAGE_KEY, name)
      onLogin(user)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message
      alert(typeof msg === 'string' ? msg : '登录失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>🌿 迷雾南塘</h1>
      <h2>生态博弈游戏</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="输入您的昵称（唯一，用于本游戏与问卷）"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={loading} style={{ width: '100%' }}>
          {loading ? '登录中…' : '登录'}
        </button>
      </form>
    </div>
  )
}

export default Login
