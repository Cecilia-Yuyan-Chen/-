import React, { useEffect, useState } from 'react'

const PHASE_INTROS = {
  1: {
    title: '迷雾村庄',
    subtitle: 'Round 1-5',
    image: '/phases/phase1.png',
    big: '在充满迷雾的村庄里，你只知道自己做了什么，无法观测到你的邻居们如何选择。',
    small: '每人初始存在10NT，初始生态值为0。所有回合结束时生态值可等效换为NT收益，总收益为结束时的NT+生态值',
    icon: '🌫️',
    accent: 'linear-gradient(135deg, #6b7fd7 0%, #8e9ed6 100%)',
  },
  2: {
    title: '公共账本',
    subtitle: 'Round 6-10',
    image: '/phases/phase2.png',
    big: '村庄里来了一个DAO，并为村庄引入了区块链公共账本，所有的行为和数据都透明可见了。',
    small: 'DAO将为使用有机肥的农户提供1.5NT的生态补贴，但为了领取补贴需要质押1.5NT在验证后返还。如果验证失败将罚没质押NT。\n玩家在选择策略后可以点击申请领取生态补贴，但请注意：无论选择使用哪种肥料都可以申请领取补贴，使用无机肥且申领补贴有一定概率被发现作弊。',
    icon: '📒',
    accent: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  },
  3: {
    title: '数字村民',
    subtitle: 'Round 11-15',
    image: '/phases/phase3.png',
    big: '由于DAO的发展，现在有一些数字村民和关系人口也在关注村子的发展。关心生态的数字村民增加了额外的生态补贴，生态补贴提高为2NT。',
    small: '由于关注度的提高，作弊被系统识别的概率提高了。且在本阶段被识破除了罚没质押NT，还不会获得任何种地收益。\n新增不信任投票的机制，每一轮中每个农户可以在宣称使用生态肥的农户中选择1人投票。票数最高的农户将被核查其真实情况，投出作弊者的玩家将平分罚没收益。',
    icon: '👥',
    accent: 'linear-gradient(135deg, #764ba2 0%, #667eea 100%)',
  },
}

function PhaseIntro({ phase, onEnter }) {
  const [visible, setVisible] = useState(false)
  const info = PHASE_INTROS[phase]

  useEffect(() => {
    const t = requestAnimationFrame(() => {
      requestAnimationFrame(() => setVisible(true))
    })
    return () => cancelAnimationFrame(t)
  }, [phase])

  if (!info) return null

  const handleEnter = () => {
    setVisible(false)
    setTimeout(onEnter, 280)
  }

  return (
    <div className={`phase-intro ${visible ? 'phase-intro--visible' : ''}`}>
      <div className="phase-intro__backdrop" />
      <div className="phase-intro__card">
        <div className="phase-intro__badge" style={{ background: info.accent }}>
          <span className="phase-intro__icon">{info.icon}</span>
          <span className="phase-intro__title">{info.title}</span>
          <span className="phase-intro__subtitle">{info.subtitle}</span>
        </div>
        {info.image && (
          <div className="phase-intro__image-wrap">
            <img src={info.image} alt={info.title} className="phase-intro__image" />
          </div>
        )}
        <p className="phase-intro__big">{info.big}</p>
        <p className="phase-intro__small">{info.small}</p>
        <button type="button" className="phase-intro__btn" onClick={handleEnter}>
          进入阶段
        </button>
      </div>
    </div>
  )
}

export default PhaseIntro
