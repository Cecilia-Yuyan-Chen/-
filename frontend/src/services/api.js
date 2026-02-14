import axios from 'axios'

// 获取API基础URL，支持局域网访问
const getApiBaseURL = () => {
  // 如果是开发环境且不在localhost，使用当前主机名
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return `http://${window.location.hostname}:8000/api`
  }
  return '/api'
}

const api = axios.create({
  baseURL: getApiBaseURL(),
  headers: {
    'Content-Type': 'application/json'
  }
})

export { api }
