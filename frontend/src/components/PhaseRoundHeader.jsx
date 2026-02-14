import React from 'react'

const PHASE_NAMES = {
  1: '阶段一：迷雾村庄',
  2: '阶段二：公共账本',
  3: '阶段三：数字村民'
}

function PhaseRoundHeader({ phase, round }) {
  const phaseName = PHASE_NAMES[phase] || `阶段${phase}`
  return (
    <div className="phase-round-header">
      <span className="phase-round-header__phase">{phaseName}</span>
      <span className="phase-round-header__sep"> · </span>
      <span className="phase-round-header__round">第 {round} / 15 轮</span>
    </div>
  )
}

export default PhaseRoundHeader
