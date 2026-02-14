import React, { useState } from 'react'
import { api } from '../services/api'

const QUESTIONS = [
  { key: 'Q1', label: 'Q1：您的公钥地址（用于NT发放）', type: 'text', placeholder: '请输入公钥地址' },
  {
    key: 'Q2',
    label: 'Q2：您的性别',
    type: 'radio',
    options: [
      { value: '男', text: '男' },
      { value: '女', text: '女' }
    ]
  },
  { key: 'Q3', label: 'Q3：您的年龄', type: 'number', placeholder: '请输入年龄', min: 1, max: 150 },
  { key: 'Q4', label: 'Q4：您的职业是？（若在校学生请填写学生+专业）', type: 'text', placeholder: '请输入' },
  {
    key: 'Q5',
    label: 'Q5：您的原生家庭是否从事过农业生产？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 是，我在农村长大/家里有地或务农' },
      { value: 'B', text: 'B. 否，我是城市长大的，且几乎没有接触过农业' },
      { value: 'C', text: 'C. 否，我是城市长大的，但对农业/乡建有一定了解或实践经验' }
    ]
  },
  {
    key: 'Q6',
    label: 'Q6：在今天参与游戏的玩家中，有多少位是您在参加本次共创营之前就认识的朋友？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 0人' },
      { value: 'B', text: 'B. 1-3人' },
      { value: 'C', text: 'C. 4人以上' }
    ]
  },
  {
    key: 'Q7',
    label: 'Q7：在参与这次共创营前，您持有过加密货币（Cryptocurrency）或NFT吗？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 从未持有' },
      { value: 'B', text: 'B. 持有过，但不太操作' },
      { value: 'C', text: 'C. 经常交易/DeFi深度用户' }
    ]
  },
  {
    key: 'Q8',
    label: 'Q8：您此前参与过DAO的治理投票吗？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 没有' },
      { value: 'B', text: 'B. 有' }
    ]
  },
  {
    key: 'Q9',
    label: 'Q9：在日常生活中，您认为自己是一个喜欢冒险的人吗？（0-10分，0为极度保守，10为极度喜欢冒险）',
    type: 'scale',
    min: 0,
    max: 10
  },
  {
    key: 'Q10',
    label: 'Q10：假设您现在面临一个选择，您更倾向于哪一个？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 直接拿走10元' },
      { value: 'B', text: 'B. 投硬币，正面得25元、反面得0元' }
    ]
  },
  {
    key: 'Q11',
    label: 'Q11：总的来说，您认为绝大多数人是值得信任的吗？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 是的，绝大多数人可信' },
      { value: 'B', text: 'B. 不，和人打交道必须非常小心' }
    ]
  },
  {
    key: 'Q12',
    label: 'Q12：在现实生活中，您是否愿意为了保护环境而牺牲一部分个人便利或金钱（例如多花钱买环保产品）？',
    type: 'radio',
    options: [
      { value: 'A', text: 'A. 非常愿意' },
      { value: 'B', text: 'B. 比较愿意' },
      { value: 'C', text: 'C. 不太愿意' },
      { value: 'D', text: 'D. 完全不愿意' }
    ]
  }
]

function Questionnaire({ user, onSubmit }) {
  const [answers, setAnswers] = useState({})
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (key, value) => {
    setAnswers(prev => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!user?.id) return
    setSubmitting(true)
    try {
      await api.post(`users/${user.id}/questionnaire`, answers)
      onSubmit(answers)
    } catch (err) {
      console.error('提交问卷失败:', err)
      alert(err.response?.data?.detail || '提交失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container">
      <h1>🌿 迷雾南塘</h1>
      <h2>问卷（共创营信息收集）</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>请完成以下问题，完成后即可创建或加入房间。</p>
      <form onSubmit={handleSubmit} className="questionnaire-form">
        {QUESTIONS.map(q => (
          <div key={q.key} className="card" style={{ marginBottom: '16px' }}>
            <label className="question-label">{q.label}</label>
            {q.type === 'text' && (
              <input
                type="text"
                placeholder={q.placeholder}
                value={answers[q.key] || ''}
                onChange={e => handleChange(q.key, e.target.value)}
                style={{ width: '100%', padding: '10px', marginTop: '8px' }}
              />
            )}
            {q.type === 'number' && (
              <input
                type="number"
                placeholder={q.placeholder}
                min={q.min}
                max={q.max}
                value={answers[q.key] ?? ''}
                onChange={e => handleChange(q.key, e.target.value)}
                style={{ width: '100%', padding: '10px', marginTop: '8px' }}
                inputMode="numeric"
              />
            )}
            {q.type === 'scale' && (
              <select
                value={answers[q.key] ?? ''}
                onChange={e => handleChange(q.key, e.target.value)}
                style={{ width: '100%', padding: '10px', marginTop: '8px' }}
              >
                <option value="">请选择 0-10 分</option>
                {Array.from({ length: (q.max - q.min) + 1 }, (_, i) => q.min + i).map(n => (
                  <option key={n} value={String(n)}>{n}分</option>
                ))}
              </select>
            )}
            {q.type === 'radio' && (
              <div className="questionnaire-options" style={{ marginTop: '8px' }}>
                {q.options.map(opt => (
                  <label key={opt.value} className="questionnaire-option">
                    <input
                      type="radio"
                      name={q.key}
                      value={opt.value}
                      checked={answers[q.key] === opt.value}
                      onChange={() => handleChange(q.key, opt.value)}
                    />
                    <span className="questionnaire-option-text">{opt.text}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
        <button type="submit" disabled={submitting} style={{ width: '100%', marginTop: '10px' }}>
          {submitting ? '提交中…' : '提交并进入大厅'}
        </button>
      </form>
    </div>
  )
}

export default Questionnaire
