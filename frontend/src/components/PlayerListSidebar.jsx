import React from 'react'

/**
 * 游戏页面左侧栏：显示本局所有玩家，已做出选择/投票的在前方方框打勾，方便大家看到谁还没选
 */
function PlayerListSidebar({ players = [], submittedPlayerIds = [], label = '已选择' }) {
  const submittedSet = new Set(Array.isArray(submittedPlayerIds) ? submittedPlayerIds : [])
  return (
    <aside className="player-list-sidebar">
      <h3 className="player-list-sidebar__title">玩家列表</h3>
      <p className="player-list-sidebar__hint">{label}</p>
      <ul className="player-list-sidebar__list">
        {(players || []).map((p) => (
          <li key={p.id} className="player-list-sidebar__item">
            <span
              className={`player-list-sidebar__check ${submittedSet.has(p.id) ? 'checked' : ''}`}
              aria-hidden
            >
              {submittedSet.has(p.id) ? '✓' : '○'}
            </span>
            <span className="player-list-sidebar__name">{p.username || `玩家${p.id}`}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}

export default PlayerListSidebar
