import { useState } from 'react'
import './App.css'

type Message = {
  role: 'assistant' | 'user'
  text: string
}

const demoAnswers: Record<string, string> = {
  'How can I help my child brush their teeth?':
    'For children, use a soft toothbrush and a small amount of fluoride toothpaste suitable for their age. Help or supervise brushing twice a day, especially before bedtime. Encourage brushing all tooth surfaces for around two minutes.',
  'My child has toothache. What should I do?':
    'Toothache can have several causes, such as decay, irritation, or infection. Arrange a dental appointment as soon as possible. Until then, avoid very hot, cold, or sugary foods. Do not place aspirin directly on the tooth or gum.',
  'When should I seek urgent dental care?':
    'Seek urgent dental advice if your child has facial swelling, a spreading infection, uncontrolled bleeding, severe pain with fever, difficulty swallowing, difficulty breathing, or a knocked-out permanent tooth.',
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: 'Hello. I can provide general information about children’s oral health. How can I help today?',
    },
  ])
  const [input, setInput] = useState('')

  const sendMessage = (question: string) => {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) return

    const answer =
      demoAnswers[trimmedQuestion] ??
      'Thank you for your question. This prototype currently demonstrates general oral-health guidance. For a specific concern, please contact a dental professional.'

    setMessages((currentMessages) => [
      ...currentMessages,
      { role: 'user', text: trimmedQuestion },
      { role: 'assistant', text: answer },
    ])

    setInput('')
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
          {Object.keys(demoAnswers).map((question) => (
            <button
              key={question}
              className="question-button"
              onClick={() => sendMessage(question)}
            >
              {question}
            </button>
          ))}
        </div>

        <div className="messages" aria-live="polite">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              {message.text}
            </div>
          ))}
        </div>

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
          />
          <button type="submit">Send</button>
        </form>

        <footer className="safety-note">
          <p>This tool does not replace professional dental advice.</p>
          <p>Seek urgent care if your child has facial swelling, difficulty breathing, severe bleeding, or worsening severe pain.</p>
        </footer>
      </section>
    </main>
  )
}

export default App