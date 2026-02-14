export function useWebSocket(gameId, playerId, onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // 获取WebSocket地址，支持局域网访问
  let host
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // 本地开发，使用代理
    host = window.location.host
  } else {
    // 局域网访问，直接连接后端端口
    host = `${window.location.hostname}:8000`
  }
  const wsUrl = `${protocol}//${host}/ws/game/${gameId}/player/${playerId}`
  
  const ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('WebSocket连接已建立')
  }
  
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      onMessage(message)
    } catch (error) {
      console.error('解析WebSocket消息失败:', error)
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
  }
  
  ws.onclose = () => {
    console.log('WebSocket连接已关闭')
  }
  
  return ws
}

export function sendMessage(ws, type, data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type,
      ...data
    }))
  } else {
    console.error('WebSocket未连接')
  }
}
