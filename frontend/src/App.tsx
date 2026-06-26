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

type QuickQuestion = {
  number: string
  title: string
  description: string
  question: string
}

const quickQuestions: QuickQuestion[] = [
  {
    number: '01',
    title: 'Everyday prevention',
    description: 'Support for toothbrushing routines',
    question: 'How can I help my child brush their teeth?',
  },
  {
    number: '02',
    title: 'Child toothache',
    description: 'What parents should do next',
    question: 'My child has toothache. What should I do?',
  },
  {
    number: '03',
    title: 'Urgent symptoms',
    description: 'When to seek urgent dental advice',
    question: 'When should I seek urgent dental care?',
  },
]

const API_URL = 'http://127.0.0.1:8000/api/chat'

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: (
        'Welcome. This demonstration prototype shows how a parent-facing '
        + 'oral-health tool can provide general guidance and highlight '
        + 'possible urgent symptoms. Choose one of the three scenarios below.'
      ),
    },
  ])

  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')

  const sendMessage = async (question: string) => {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion || isSending) {
      return
    }

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
        'Unable to reach the local support service. Check that the FastAPI backend is running.',
      )
    } finally {
      setIsSending(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="chat-card">
        <header className="app-header">
          <div className="brand-mark" aria-hidden="true">
            🦷
          </div>

          <div className="brand-copy">
            <p className="eyebrow">University project · demonstration prototype</p>
            <h1>Children’s Oral Health Support</h1>
            <p className="subheading">
              Parent-facing guidance and safety-routing prototype
            </p>
          </div>

          <span className="status-chip">UK context</span>
        </header>

        <section className="prototype-summary">
          <p className="summary-label">CURRENT DEMONSTRATION</p>
          <h2>Safe guidance while the clinical knowledge base is pending</h2>
          <p>
            This build demonstrates an API-connected chat interface with
            three parent pathways and a safety-first urgent-symptom route.
          </p>

          <div className="prototype-points">
            <span>3 parent pathways</span>
            <span>Safety prompts</span>
            <span>API connected</span>
          </div>
        </section>

        <section className="scenario-section" aria-label="Demonstration scenarios">
          <div className="section-heading">
            <p>Demonstration scenarios</p>
            <span>Select one to test</span>
          </div>

          <div className="quick-questions">
            {quickQuestions.map((item) => (
              <button
                key={item.number}
                className="question-button"
                onClick={() => sendMessage(item.question)}
                disabled={isSending}
              >
                <span className="question-number">{item.number}</span>
                <span className="question-content">
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </span>
                <span className="question-arrow" aria-hidden="true">
                  →
                </span>
              </button>
            ))}
          </div>
        </section>

        <section
          className="messages"
          aria-live="polite"
          aria-busy={isSending}
          aria-label="Chat messages"
        >
          {messages.map((message, index) => (
            <article
              key={index}
              className={`message ${message.role} ${
                message.urgent ? 'urgent' : ''
              }`}
            >
              {message.urgent && (
                <span className="message-label">Urgent pathway</span>
              )}
              <p>{message.text}</p>
            </article>
          ))}
        </section>

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
            placeholder="Ask a general question..."
            aria-label="Ask a general question"
            disabled={isSending}
          />
          <button type="submit" disabled={isSending}>
            {isSending ? 'Sending…' : 'Send'}
          </button>
        </form>

        <footer className="safety-note">
          <p>
            <strong>Safety note:</strong> This is a university demonstration
            prototype. It does not replace professional dental advice and is
            not an NHS service.
          </p>
          <p>
            For urgent dental advice, contact a dentist or NHS 111. Call 999
            or go to A&amp;E for life-threatening symptoms.
          </p>
        </footer>
      </section>
    </main>
  )
}

export default App
