import React, { useState, useEffect } from 'react'
import Login from './components/Login'
import Questionnaire from './components/Questionnaire'
import Lobby from './components/Lobby'
import PhaseIntro from './components/PhaseIntro'
import GamePhase1 from './components/GamePhase1'
import GamePhase2 from './components/GamePhase2'
import GamePhase3 from './components/GamePhase3'
import Results from './components/Results'
import { useWebSocket } from './services/websocket'
import { api } from './services/api'

function App() {
  const [user, setUser] = useState(null)
  const [game, setGame] = useState(null)
  const [player, setPlayer] = useState(null)
  const [gameState, setGameState] = useState(null)
  const [ws, setWs] = useState(null)
  const [phaseIntroDismissed, setPhaseIntroDismissed] = useState(null)

  // 游戏结束或离开房间时重置阶段介绍，下次进入会再显示
  useEffect(() => {
    if (!game || gameState?.status === 'finished') {
      setPhaseIntroDismissed(null)
    }
  }, [game, gameState?.status])

  // WebSocket连接
  useEffect(() => {
    if (game && player) {
      const websocket = useWebSocket(game.id, player.id, (message) => {
        handleWebSocketMessage(message)
      })
      setWs(websocket)
      return () => {
        if (websocket) websocket.close()
      }
    }
  }, [game, player])

  const handleWebSocketMessage = (message) => {
    const { type } = message
    // 使用函数式更新避免闭包导致 state 丢失（如 status: 'playing'）
    if (type === 'game_started') {
      setGameState(prev => ({
        ...prev,
        status: 'playing',
        current_round: message.current_round,
        phase: message.phase
      }))
    } else if (type === 'round_result') {
      setGameState(prev => ({
        ...prev,
        round_result: message,
        voting_phase: false
      }))
    } else if (type === 'next_round') {
      setGameState(prev => ({
        ...prev,
        current_round: message.current_round,
        phase: message.phase,
        round_result: null,
        broadcast: null,
        phase2_broadcasts: null,
        voting_phase: false,
        ...(message.players && { players: message.players })
      }))
    } else if (type === 'phase2_broadcasts') {
      setGameState(prev => ({ ...prev, phase2_broadcasts: message }))
    } else if (type === 'subsidy_applied') {
      setGameState(prev => ({ ...prev, broadcast: message }))
    } else if (type === 'subsidy_caught') {
      setGameState(prev => ({ ...prev, broadcast: message }))
    } else if (type === 'vote_result') {
      setGameState(prev => ({ ...prev, broadcast: message }))
    } else if (type === 'voting_start') {
      setGameState(prev => ({
        ...prev,
        voting_phase: true,
        voting_applicants: message.applicants || []
      }))
    } else if (type === 'game_finished') {
      setGameState(prev => ({ ...prev, status: 'finished' }))
    }
  }

  const handleLogin = (userFromServer) => {
    setUser(userFromServer)
  }

  const handleQuestionnaireDone = (answers) => {
    setUser(prev => (prev ? { ...prev, questionnaire_answers: answers } : prev))
  }

  const handleCreateGame = async () => {
    if (!user?.username?.trim()) {
      alert('请先输入昵称')
      return
    }
    try {
      const params = user.id ? { user_id: user.id } : { username: user.username.trim() }
      const response = await api.post('/games/create', null, {
        params
      })
      const data = response.data
      setGame({
        id: data.id,
        game_code: data.game_code,
        creator_id: data.creator_id,
        status: data.status,
        current_round: data.current_round,
        phase: data.phase
      })
      setPlayer({ id: data.player_id })
      await loadGameState(data.id)
    } catch (error) {
      console.error('创建游戏失败:', error)
      alert(error.response?.data?.detail || '创建游戏失败，请重试')
    }
  }

  const handleJoinGame = async (gameId) => {
    if (!user?.username?.trim()) {
      alert('请先输入昵称')
      return
    }
    try {
      const params = user.id ? { user_id: user.id } : { username: user.username.trim() }
      const response = await api.post(`/games/${gameId}/join`, null, {
        params
      })
      setPlayer({ id: response.data.player_id })
      const gameResponse = await api.get(`/games/${gameId}`)
      const gameData = gameResponse.data
      setGame(gameData)
      await loadGameState(gameId, gameData)
    } catch (error) {
      console.error('加入游戏失败:', error)
      alert(error.response?.data?.detail || '加入游戏失败，请重试')
    }
  }

  const loadGameState = async (gameId, gameFromApi = null) => {
    try {
      const game = gameFromApi || (await api.get(`/games/${gameId}`)).data
      const players = (await api.get(`/games/${gameId}/players`)).data
      setGameState({
        players,
        status: game.status,
        current_round: game.current_round ?? 0,
        phase: game.phase ?? 1
      })
    } catch (error) {
      console.error('加载游戏状态失败:', error)
    }
  }

  const handleStartGame = async () => {
    try {
      await api.post(`/games/${game.id}/start`, null, {
        params: { player_id: player.id }
      })
    } catch (error) {
      console.error('开始游戏失败:', error)
      alert(error.response?.data?.detail || '开始游戏失败，请重试')
    }
  }

  // 渲染当前页面
  if (!user) {
    return <Login onLogin={handleLogin} />
  }

  // 问卷：已登录但未填问卷则先填问卷，再进入大厅
  const hasQuestionnaire = user.questionnaire_answers && Object.keys(user.questionnaire_answers).length > 0
  if (user && !hasQuestionnaire) {
    return (
      <Questionnaire
        user={user}
        onSubmit={handleQuestionnaireDone}
      />
    )
  }

  // 大厅：未加入房间 或 已加入但游戏未开始（waiting）
  const showLobby = !game || !player || gameState?.status === 'waiting' || !gameState
  if (showLobby) {
    return (
      <Lobby
        user={user}
        player={player}
        game={game}
        gameState={gameState}
        onCreateGame={handleCreateGame}
        onJoinGame={handleJoinGame}
        onStartGame={handleStartGame}
        onLoadGameState={loadGameState}
      />
    )
  }

  if (gameState?.status === 'finished') {
    return <Results game={game} player={player} />
  }

  if (gameState?.status === 'playing') {
    const phase = gameState.phase || 1
    const round = gameState.current_round || 1
    const isFirstRoundOfPhase = (phase === 1 && round === 1) || (phase === 2 && round === 6) || (phase === 3 && round === 11)
    const showPhaseIntro = isFirstRoundOfPhase && phaseIntroDismissed !== phase

    const dismissPhaseIntro = () => setPhaseIntroDismissed(phase)

    if (showPhaseIntro) {
      return (
        <PhaseIntro phase={phase} onEnter={dismissPhaseIntro} />
      )
    }

    if (phase === 1) {
      return (
        <GamePhase1
          game={game}
          player={player}
          gameState={gameState}
          ws={ws}
        />
      )
    } else if (phase === 2) {
      return (
        <GamePhase2
          game={game}
          player={player}
          gameState={gameState}
          ws={ws}
        />
      )
    } else if (phase === 3) {
      return (
        <GamePhase3
          game={game}
          player={player}
          gameState={gameState}
          ws={ws}
        />
      )
    }
  }

  return <div className="loading">加载中...</div>
}

export default App
