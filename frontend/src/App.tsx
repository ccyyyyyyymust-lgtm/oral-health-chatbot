import { useState } from 'react'
import './App.css'

type Role = 'assistant' | 'user'

type Message = {
  role: Role
  text: string
  urgent?: boolean
  sources?: SourceLink[]
  needsAgeGroup?: boolean
  pendingQuestion?: string
  dentalServices?: DentalService[]
  copyablePostcode?: string
}

type SourceLink = {
  title: string
  url: string
}

type DentalService = {
  name: string
  address: string
  postcode: string
  phone: string
  map_url: string
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
  dental_services: DentalService[]
  copyable_postcode: string | null
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

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const input = document.createElement('textarea')
  input.value = text
  input.setAttribute('readonly', '')
  input.style.position = 'fixed'
  input.style.opacity = '0'
  document.body.appendChild(input)
  input.select()
  document.execCommand('copy')
  input.remove()
}

function App() {
  const [messages, setMessages] = useState<Message[]>([welcomeMessage])
  const [input, setInput] = useState('')
  const [region, setRegion] = useState<Region>('Not sure')
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('Not provided')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')

  const sendMessage = async (
    question: string,
    options: {
      ageOverride?: AgeGroup
      showUserMessage?: boolean
      replaceAgePrompt?: boolean
    } = {},
  ) => {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isSending) return

    const userMessage: Message = { role: 'user', text: trimmedQuestion }
    const originalMessages = messages
    const baseMessages = options.replaceAgePrompt ? messages.slice(0, -1) : messages
    const updatedMessages = options.showUserMessage === false
      ? baseMessages
      : [...baseMessages, userMessage]
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
          age_group: options.ageOverride ?? ageGroup,
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
          needsAgeGroup: data.needs_age_group,
          pendingQuestion: data.needs_age_group ? trimmedQuestion : undefined,
          dentalServices: data.dental_services,
          copyablePostcode: data.copyable_postcode ?? undefined,
        },
      ])
    } catch (requestError) {
      if (options.replaceAgePrompt) {
        setMessages(originalMessages)
      }
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

  const selectAgeAndRetry = (selectedAge: Exclude<AgeGroup, 'Not provided'>, question: string) => {
    if (isSending) return
    setAgeGroup(selectedAge)
    void sendMessage(question, {
      ageOverride: selectedAge,
      showUserMessage: false,
      replaceAgePrompt: true,
    })
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

        {(region === 'Not sure' || ageGroup === 'Not provided') && (
          <aside className="context-reminder" role="note" aria-label="Before asking">
            <strong>Before asking</strong>
            <span>
              Please select your location and your child’s age. This helps us
              provide more relevant guidance.
            </span>
          </aside>
        )}

        <section className="context-section" aria-label="Parent context">
          <label className={region === 'Not sure' ? 'needs-attention' : ''}>
            <span>Location</span>
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value as Region)}
              disabled={isSending}
              aria-describedby={region === 'Not sure' ? 'location-selection-hint' : undefined}
            >
              {regions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            {region === 'Not sure' && <small id="location-selection-hint">Please select</small>}
          </label>
          <label className={ageGroup === 'Not provided' ? 'needs-attention' : ''}>
            <span>Child age</span>
            <select
              value={ageGroup}
              onChange={(event) => setAgeGroup(event.target.value as AgeGroup)}
              disabled={isSending}
              aria-describedby={ageGroup === 'Not provided' ? 'age-selection-hint' : undefined}
            >
              {ageGroups.map((item) => (
                <option key={item} value={item}>
                  {item === 'Not provided' ? 'Not provided yet' : item}
                </option>
              ))}
            </select>
            {ageGroup === 'Not provided' && <small id="age-selection-hint">Please select</small>}
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
              {message.copyablePostcode && (
                <div className="postcode-copy-card" aria-label="Postcode to copy">
                  <strong>{message.copyablePostcode}</strong>
                  <div className="postcode-actions">
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`dentist near ${message.copyablePostcode}`)}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open in maps
                    </a>
                    <button type="button" onClick={() => void copyText(message.copyablePostcode!)}>
                      Copy postcode
                    </button>
                  </div>
                </div>
              )}
              {message.dentalServices && message.dentalServices.length > 0 && (
                <div className="dental-service-list" aria-label="Dental practices">
                  {message.dentalServices.map((service) => (
                    <section className="dental-service" key={`${service.name}-${service.postcode}`}>
                      <strong>{service.name}</strong>
                      {service.address && <span>{service.address}</span>}
                      {service.postcode && <span>{service.postcode}</span>}
                      {service.phone && <a href={`tel:${service.phone}`}>{service.phone}</a>}
                      <div className="service-actions">
                        <a href={service.map_url} target="_blank" rel="noreferrer">Open in maps</a>
                        {service.postcode && (
                          <button
                            type="button"
                            onClick={() => void copyText(service.postcode)}
                          >
                            Copy postcode
                          </button>
                        )}
                      </div>
                    </section>
                  ))}
                </div>
              )}
              {message.needsAgeGroup && message.pendingQuestion && (
                <div className="age-choice-group" aria-label="Choose the child's age group">
                  {(['0-3', '3-6', '7+'] as const).map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => selectAgeAndRetry(item, message.pendingQuestion!)}
                      disabled={isSending}
                    >
                      {item === '0-3' ? '0–3 years' : item === '3-6' ? '3–6 years' : '7+ years'}
                    </button>
                  ))}
                </div>
              )}
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
