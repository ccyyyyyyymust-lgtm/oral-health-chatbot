import { useState } from 'react'
import './App.css'

type Message = {
  role: 'assistant' | 'user'
  text: string
  urgent?: boolean
}

type ChatApiResponse = {
  reply: string
  category: 'general' | 'brushing' | 'toothache' | 'urgent'
  urgent: boolean
}

const quickQuestions = [
  'How can I help my child brush their teeth?',
  'My child has toothache. What should I do?',
  'When should I seek urgent dental care?',
]

const API_URL = 'http://127.0.0.1:8000/api/chat'

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: 'Hello. I can provide general information about children’s oral health. How can I help today?',
    },
  ])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')

  const sendMessage = async (question: string) => {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion || isSending) return

    setMessages((currentMessages) => [
      ...currentMessages,
      { role: 'user', text: trimmedQuestion },
    ])

    setInput('')
    setError('')
    setIsSending(true)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: trimmedQuestion }),
      })

      if (!response.ok) {
        throw new Error('The API returned an error.')
      }

      const data: ChatApiResponse = await response.json()

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          text: data.reply,
          urgent: data.urgent,
        },
      ])
    } catch {
      setError(
        'Unable to reach the local support service. Please check that the backend is running.',
      )
    } finally {
      setIsSending(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="chat-card">
        <header className="app-header">
          <div className="logo">🦷</div>
          <div>
            <p className="eyebrow">Parent support prototype</p>
            <h1>Children’s Oral Health</h1>
          </div>
        </header>

        <div className="intro">
          <h2>How can I help?</h2>
          <p>
            Ask a general question about your child’s oral health, brushing,
            toothache, or when to seek help.
          </p>
        </div>

        <div className="quick-questions">
          {quickQuestions.map((question) => (
            <button
              key={question}
              className="question-button"
              onClick={() => sendMessage(question)}
              disabled={isSending}
            >
              {question}
            </button>
          ))}
        </div>

        <div className="messages" aria-live="polite" aria-busy={isSending}>
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.role} ${
                message.urgent ? 'urgent' : ''
              }`}
            >
              {message.text}
            </div>
          ))}
        </div>

        {error && <p className="error-message">{error}</p>}

        <form
          className="message-form"
          onSubmit={(event) => {
            event.preventDefault()
            sendMessage(input)
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Type a question..."
            aria-label="Type a question"
            disabled={isSending}
          />
          <button type="submit" disabled={isSending}>
            {isSending ? 'Sending...' : 'Send'}
          </button>
        </form>

        <footer className="safety-note">
          <p>This tool does not replace professional dental advice.</p>
          <p>
            Seek urgent care if your child has facial swelling, difficulty
            breathing, severe bleeding, or worsening severe pain.
          </p>
        </footer>
      </section>
    </main>
  )
}

export default App