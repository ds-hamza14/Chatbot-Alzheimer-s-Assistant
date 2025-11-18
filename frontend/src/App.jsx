import { useState } from "react"
import Chatbot from "./components/Chatbot"
import Disclaimer from "./components/Disclaimer"
import "./App.css"

function App() {
  const [showChat, setShowChat] = useState(false)

  return (
    <div className="app">
      {!showChat ? (
        <div className="start-screen">
          <header className="app-header">
            <h1>Alzheimer's Symptom Assessment</h1>
            <p>AI-powered preliminary screening tool</p>
          </header>

          <button onClick={() => setShowChat(true)} className="start-btn">
            Start Conversation
          </button>

          <Disclaimer />
        </div>
      ) : (
        <div className="chat-screen">
          <Chatbot onClose={() => setShowChat(false)} />
        </div>
      )}
    </div>
  )
}

export default App
