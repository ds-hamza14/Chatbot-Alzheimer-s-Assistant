import { useState, useEffect, useRef } from 'react'
import './Chatbot.css'

function Chatbot({ onClose }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        "Hello, I'm your Alzheimer's Health Assistant 🤖. How can I help you today?",
    },
  ])
  const [assessmentStage, setAssessmentStage] = useState('qa')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentSymptomIndex, setCurrentSymptomIndex] = useState(1)
  const [answers, setAnswers] = useState({})

  // 🔹 Ref for chat window
  const chatWindowRef = useRef(null)

  // 🔹 Auto scroll whenever messages change
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTo({
        top: chatWindowRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages, loading])

  const postTo = async (url, payload) => {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  }

  const pushAssistant = (text) =>
    setMessages((prev) => [...prev, { role: 'assistant', text }])

  const pushUser = (text) =>
    setMessages((prev) => [...prev, { role: 'user', text }])

  const sendMessage = async () => {
    if (!input.trim()) return
    const userText = input.trim()
    pushUser(userText)
    setInput('')
    setLoading(true)

    try {
      let data
      if (assessmentStage === 'open_conversation') {
        // Free chat mode
        data = await postTo('http://localhost:5000/api/open-conversation', {
          conversation: [...messages, { role: 'user', text: userText }],
        })
      } else {
        // Symptom extraction / QA flow
        data = await postTo('http://localhost:5000/api/extract-symptoms', {
          conversation: [...messages, { role: 'user', text: userText }],
          assessment_stage: assessmentStage,
          current_symptom_index: currentSymptomIndex,
          answered: { ...answers }, // ✅ ensure up-to-date clone is sent
        })
      }

      if (data.success) {
        if (data.answer) pushAssistant(data.answer)
        if (data.confirmation) pushAssistant(data.confirmation)
        if (data.next_question) pushAssistant(data.next_question)

        if (data.assessment_stage === 'symptom_qa' && data.question) {
          // Use backend’s actual index (not local)
          const backendIndex = data.current_symptom_index ?? currentSymptomIndex
          const numberedQ = data.question.replace(
            /\d+\/15/,
            `${backendIndex + 1}/15`,
          )
          pushAssistant(numberedQ)

          // ✅ Sync exact index and answers from backend
          setCurrentSymptomIndex(backendIndex)
          if (data.answered) setAnswers(data.answered)
        }

        if (data.assessment_stage === 'done') {
          pushAssistant('📊 Prediction Result is being prepared...')
          submitForPrediction(data.answered)
        }

        if (data.assessment_stage) setAssessmentStage(data.assessment_stage)
        if (data.next_stage) setAssessmentStage(data.next_stage) // ✅ use backend next_stage
      } else {
        pushAssistant('⚠️ Server error.')
      }
    } catch (e) {
      console.error(e)
      pushAssistant('⚠️ Server error.')
    } finally {
      setLoading(false)
    }
  }

  const submitForPrediction = async (finalAnswers) => {
    setLoading(true)
    try {
      const positives = Object.keys(finalAnswers).filter(
        (k) => finalAnswers[k] === true,
      )
      const data = await postTo('http://localhost:5000/api/predict', {
        symptoms: positives,
      })

      if (data.success) {
        pushAssistant(
          `📊 Prediction Result:\nLikelihood: ${data.prediction.likelihood}%\nMessage: ${data.prediction.message}\nADNI1 Confidence: ${data.prediction.adni1_confidence}%\nADNIGO Confidence: ${data.prediction.adnigo_confidence}%`,
        )
        // ✅ Instead of locking "done", continue into free chat
        if (data.next_stage) {
          setAssessmentStage(data.next_stage)
        } else {
          setAssessmentStage('open_conversation')
        }
      } else {
        pushAssistant('⚠️ Prediction failed.')
      }
    } catch (e) {
      console.error(e)
      pushAssistant('⚠️ Server error during prediction.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') routeSend()
  }

  const routeSend = () => {
    if (!input.trim()) return
    sendMessage()
  }

  return (
    <div className="chatbot-container">
      <div className="chat-header">
        <h2>Alzheimer’s Assistant</h2>
        <button onClick={onClose} className="close-btn">
          ✖
        </button>
      </div>

      {/* 🔹 Chat window with auto-scroll */}
      <div className="chat-window" ref={chatWindowRef}>
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {loading && <div className="chat-bubble assistant">Typing...</div>}
      </div>

      {assessmentStage !== 'done' && (
        <div className="chat-input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response..."
          />
          <button onClick={routeSend} className="send-btn">
            Send
          </button>
        </div>
      )}
    </div>
  )
}

export default Chatbot
