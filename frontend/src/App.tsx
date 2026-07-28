import { useState } from 'react'
import './App.css'

type Role = 'assistant' | 'user'

type Message = {
  role: Role
  text: string
  urgent?: boolean
  sources?: SourceLink[]
}

type SourceLink = {
  title: string
  url: string
}

type ChatApiResponse = {
  reply: string
  category: 'general' | 'brushing' | 'toothache' | 'urgent'
  urgent: boolean
  region: Region
  age_group: AgeGroup
  needs_age_group: boolean
  source_gap: boolean
  sources: SourceLink[]
  response_mode: 'safety' | 'llm' | 'fallback'
}

type QuickQuestion = {
  number: string
  title: string
  description: string
  question: string
}

type Region =
  | 'England'
  | 'Wales'
  | 'Scotland'
  | 'Northern Ireland'
  | 'Not sure'

type AgeGroup = 'Not provided' | '0-3' | '3-6' | '7+'

const regions: Region[] = [
  'England',
  'Wales',
  'Scotland',
  'Northern Ireland',
  'Not sure',
]

const ageGroups: AgeGroup[] = ['Not provided', '0-3', '3-6', '7+']

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

const API_URL =
  import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/chat'

const welcomeMessage: Message = {
  role: 'assistant',
  text: (
    'Welcome. Describe your child’s oral-health question in your own words. '
    + 'I can provide general information, highlight urgent warning signs, '
    + 'and show the reviewed sources used.'
  ),
}

function App() {
  const [messages, setMessages] = useState<Message[]>([welcomeMessage])
  const [input, setInput] = useState('')
  const [region, setRegion] = useState<Region>('Not sure')
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('Not provided')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')

  const sendMessage = async (question: string) => {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isSending) return

    const userMessage: Message = { role: 'user', text: trimmedQuestion }
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setInput('')
    setError('')
    setIsSending(true)

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), 15_000)

    try {
      const conversation = updatedMessages
        .slice(1)
        .slice(-10)
        .map((message) => ({
          role: message.role,
          content: message.text,
        }))

      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: conversation,
          region,
          age_group: ageGroup,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        if (response.status === 429) {
          throw new Error('Too many messages. Please wait a minute and try again.')
        }
        throw new Error(body?.detail ?? 'The support service returned an error.')
      }

      const data: ChatApiResponse = await response.json()
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          text: data.reply,
          urgent: data.urgent,
          sources: data.sources,
        },
      ])
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === 'AbortError') {
        setError('The response took too long. Please check your connection and try again.')
      } else if (requestError instanceof Error) {
        setError(requestError.message)
      } else {
        setError('Unable to reach the support service. Please try again shortly.')
      }
    } finally {
      window.clearTimeout(timeoutId)
      setIsSending(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="chat-card">
        <header className="app-header">
          <div className="brand-mark" aria-hidden="true">🦷</div>
          <div className="brand-copy">
            <p className="eyebrow">University project · demonstration prototype</p>
            <h1>Children’s Oral Health Support</h1>
            <p className="subheading">Parent-facing guidance and safety routing</p>
          </div>
          <span className="status-chip">UK context</span>
        </header>

        <section className="prototype-summary">
          <p className="summary-label">CURRENT DEMONSTRATION</p>
          <h2>Ask an oral-health question in your own words</h2>
          <p>
            Answers use reviewed NHS and Delivering Better Oral Health sources.
            The chatbot provides general information and does not diagnose.
          </p>
          <div className="prototype-points">
            <span>Conversation context</span>
            <span>Safety checks</span>
            <span>Source links</span>
          </div>
        </section>

        <section className="context-section" aria-label="Parent context">
          <label>
            <span>Location</span>
            <select value={region} onChange={(event) => setRegion(event.target.value as Region)} disabled={isSending}>
              {regions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span>Child age</span>
            <select value={ageGroup} onChange={(event) => setAgeGroup(event.target.value as AgeGroup)} disabled={isSending}>
              {ageGroups.map((item) => (
                <option key={item} value={item}>
                  {item === 'Not provided' ? 'Not provided yet' : item}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="scenario-section" aria-label="Example questions">
          <div className="section-heading">
            <p>Example questions</p>
            <span>Or type your own below</span>
          </div>
          <div className="quick-questions">
            {quickQuestions.map((item) => (
              <button key={item.number} className="question-button" onClick={() => sendMessage(item.question)} disabled={isSending}>
                <span className="question-number">{item.number}</span>
                <span className="question-content">
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </span>
                <span className="question-arrow" aria-hidden="true">→</span>
              </button>
            ))}
          </div>
        </section>

        <section className="messages" aria-live="polite" aria-busy={isSending} aria-label="Chat messages">
          {messages.map((message, index) => (
            <article key={index} className={`message ${message.role} ${message.urgent ? 'urgent' : ''}`}>
              {message.urgent && <span className="message-label">Urgent pathway</span>}
              <p>{message.text}</p>
              {message.sources && message.sources.length > 0 && (
                <div className="source-links" aria-label="Sources">
                  <span>Reviewed sources</span>
                  {message.sources.map((source) => (
                    <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                  ))}
                </div>
              )}
            </article>
          ))}
          {isSending && <p className="sending-status">Reviewing your question…</p>}
        </section>

        {error && <p className="error-message" role="alert">{error}</p>}

        <form className="message-form" onSubmit={(event) => { event.preventDefault(); sendMessage(input) }}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Describe the question or symptom…"
            aria-label="Describe the question or symptom"
            disabled={isSending}
            maxLength={500}
          />
          <button type="submit" disabled={isSending || !input.trim()}>
            {isSending ? 'Sending…' : 'Send'}
          </button>
        </form>

        <footer className="safety-note">
          <p><strong>Safety note:</strong> This university prototype does not replace professional dental advice and is not an NHS service.</p>
          <p>For urgent dental advice, contact a dentist or NHS 111. Call 999 or go to A&amp;E for life-threatening symptoms.</p>
        </footer>
      </section>
    </main>
  )
}

export default App
