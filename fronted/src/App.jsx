import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  Activity, ArrowRight, BarChart3, Bot, CheckCircle2,
  Database, DollarSign, LayoutDashboard, LoaderCircle,
  Menu, MessageSquare, Send, ShieldCheck, Sparkles,
  TrendingUp, X,
} from 'lucide-react'

const API_BASE = '/api'

const suggestedQuestions = [
  'Who are the top 5 suppliers by total spending?',
  'Which departments have the highest total spending?',
  'What are the top 10 most purchased items?',
  'How much was spent in each fiscal year?',
]

function formatCurrency(value) {
  if (typeof value !== 'number') return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value)
}

function formatNumber(value) {
  if (typeof value !== 'number') return '—'
  return new Intl.NumberFormat('en-US').format(value)
}

function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({ purchases: null, spending: null })
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState('')
  const [chatError, setChatError] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    async function loadStats() {
      try {
        const [statsResponse, spendingResponse] = await Promise.all([
          fetch(`${API_BASE}/stats`),
          fetch(`${API_BASE}/total-spending`),
        ])
        if (!statsResponse.ok || !spendingResponse.ok) {
          throw new Error('Failed to load statistics')
        }
        const statsData = await statsResponse.json()
        const spendingData = await spendingResponse.json()
        setStats({
          purchases: statsData.total_purchases,
          spending: spendingData.total_spending,
        })
      } catch {
        setStatsError('Statistics are temporarily unavailable.')
      } finally {
        setStatsLoading(false)
      }
    }
    loadStats()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function askQuestion(text) {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setActivePage('assistant')
    setSidebarOpen(false)
    setQuestion('')
    setChatError('')
    setLoading(true)
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }])

    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed }),
      })
      if (!response.ok) throw new Error('Request failed')
      const data = await response.json()
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer || 'No answer was returned.',
        },
      ])
    } catch {
      setChatError('Unable to get an answer. Please check the backend.')
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    askQuestion(question)
  }

  function changePage(page) {
    setActivePage(page)
    setSidebarOpen(false)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-[#0b1730] text-white transition-transform duration-300 lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-7">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500">
              <Sparkles size={23} />
            </div>
            <div>
              <h1 className="text-base font-bold">ProcureAI</h1>
              <p className="text-xs text-slate-400">Procurement Intelligence</p>
            </div>
          </div>
          <button type="button" className="lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <div className="px-4 pt-8">
          <p className="mb-4 px-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Workspace
          </p>
          <nav className="space-y-2">
            <button type="button" onClick={() => changePage('dashboard')}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-medium ${activePage === 'dashboard' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-white/10'}`}>
              <LayoutDashboard size={19} /> Dashboard
            </button>
            <button type="button" onClick={() => changePage('assistant')}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-medium ${activePage === 'assistant' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-white/10'}`}>
              <MessageSquare size={19} /> AI Assistant
            </button>
          </nav>
        </div>

        <div className="mt-auto p-5">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck size={17} className="text-emerald-400" /> Data access
            </div>
            <p className="text-xs leading-6 text-slate-400">
              Procurement analytics powered by AI and read-only database queries.
            </p>
          </div>
          <p className="mt-5 text-center text-xs text-slate-500">
            AI Procurement Assistant · v1.0
          </p>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-72">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-5 md:px-10">
          <div className="flex items-center gap-4">
            <button type="button" className="rounded-lg p-2 lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu size={23} />
            </button>
            <div>
              <p className="text-xs font-medium text-slate-400">Procurement Analytics Platform</p>
              <h2 className="text-lg font-bold">
                {activePage === 'dashboard' ? 'Overview Dashboard' : 'AI Procurement Assistant'}
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            Local workspace
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-5 py-8 md:px-10">
          {activePage === 'dashboard' ? (
            <>
              <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0d2246] via-[#12396f] to-[#1d64b4] p-8 text-white md:p-10">
                <div className="relative z-10 max-w-2xl">
                  <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold">
                    <Sparkles size={14} /> AI-Powered Analytics
                  </div>
                  <h2 className="text-3xl font-bold leading-tight md:text-4xl">
                    Smarter procurement<br />starts with better insights.
                  </h2>
                  <p className="mt-4 max-w-xl text-sm leading-7 text-blue-100">
                    Explore purchasing data, discover spending patterns,
                    and ask questions using natural language.
                  </p>
                  <button type="button" onClick={() => changePage('assistant')}
                    className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-blue-900">
                    Ask AI Assistant <ArrowRight size={17} />
                  </button>
                </div>
                <div className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full border-[55px] border-white/5" />
              </section>

              <section className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                <StatCard title="Total Purchases"
                  value={statsLoading ? 'Loading...' : formatNumber(stats.purchases)}
                  icon={Database} subtitle="Procurement records" color="blue" />
                <StatCard title="Total Spending"
                  value={statsLoading ? 'Loading...' : formatCurrency(stats.spending)}
                  icon={DollarSign} subtitle="Across all purchases" color="emerald" />
                <StatCard title="AI Analytics" value="Ready"
                  icon={Activity} subtitle="Natural language queries" color="violet" />
              </section>

              {statsError && <p className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">{statsError}</p>}

              <section className="mt-8 grid gap-6 xl:grid-cols-5">
                <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm xl:col-span-3">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-blue-50 p-3 text-blue-600"><BarChart3 size={21} /></div>
                    <div>
                      <h3 className="font-bold">Explore Your Data</h3>
                      <p className="text-sm text-slate-500">Start with a suggested procurement question</p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {suggestedQuestions.map((item) => (
                      <button key={item} type="button" onClick={() => askQuestion(item)}
                        className="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-200 px-4 py-4 text-left text-sm text-slate-700 hover:border-blue-300 hover:bg-blue-50">
                        <span>{item}</span><ArrowRight size={17} className="shrink-0 text-blue-500" />
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm xl:col-span-2">
                  <div className="mb-6 flex items-center gap-3">
                    <div className="rounded-xl bg-violet-50 p-3 text-violet-600"><TrendingUp size={21} /></div>
                    <div>
                      <h3 className="font-bold">How It Works</h3>
                      <p className="text-sm text-slate-500">From question to insight</p>
                    </div>
                  </div>
                  <div className="space-y-6">
                    {[
                      ['01', 'Ask a question', 'Use everyday language.'],
                      ['02', 'Generate a query', 'AI creates a database query.'],
                      ['03', 'Validate and execute', 'The backend checks and runs it.'],
                      ['04', 'Get an answer', 'Results become readable insights.'],
                    ].map(([number, title, description]) => (
                      <div key={number} className="flex gap-4">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-600">{number}</div>
                        <div>
                          <p className="text-sm font-semibold">{title}</p>
                          <p className="mt-1 text-xs text-slate-500">{description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </>
          ) : (
            <section className="flex h-[calc(100vh-9rem)] min-h-[550px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-white">
                  <Bot size={24} />
                </div>
                <div>
                  <h3 className="font-bold">ProcureAI Assistant</h3>
                  <p className="text-xs text-slate-500">Ask questions about procurement data</p>
                </div>
                <div className="ml-auto flex items-center gap-2 text-xs font-medium text-emerald-600">
                  <CheckCircle2 size={15} /> Ready
                </div>
              </div>

              <div className="flex-1 space-y-6 overflow-y-auto bg-slate-50/60 px-5 py-7 md:px-8">
                {messages.length === 0 && (
                  <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center text-center">
                    <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-blue-100 text-blue-600">
                      <Sparkles size={35} />
                    </div>
                    <h3 className="text-2xl font-bold">What would you like to know?</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-500">
                      Ask about suppliers, departments, purchasing trends,
                      or spending patterns in your procurement database.
                    </p>
                    <div className="mt-7 grid w-full gap-3 sm:grid-cols-2">
                      {suggestedQuestions.map((item) => (
                        <button key={item} type="button" onClick={() => askQuestion(item)}
                          className="rounded-xl border border-slate-200 bg-white p-4 text-left text-xs leading-6 text-slate-600 hover:border-blue-300 hover:bg-blue-50">
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((message, index) => (
                  <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[90%] rounded-2xl px-5 py-4 text-sm leading-7 md:max-w-[80%] ${
                      message.role === 'user'
                        ? 'rounded-br-sm bg-blue-600 text-white'
                        : 'rounded-bl-sm border border-slate-200 bg-white text-slate-700 shadow-sm'
                    }`}>
                      {message.role === 'assistant' && (
                        <div className="mb-2 flex items-center gap-2 text-xs font-bold text-blue-600">
                          <Sparkles size={14} /> AI Answer
                        </div>
                      )}

                      {/* Markdown formatting fixes the ** symbols */}
                      <div className="break-words">
                        {message.role === 'assistant' ? (
                          <ReactMarkdown
                            components={{
                              p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                              strong: ({ children }) => <strong className="font-bold text-slate-900">{children}</strong>,
                              ol: ({ children }) => <ol className="my-3 list-decimal space-y-2 pl-5">{children}</ol>,
                              ul: ({ children }) => <ul className="my-3 list-disc space-y-2 pl-5">{children}</ul>,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        ) : (
                          <span className="whitespace-pre-wrap">{message.content}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-500 shadow-sm">
                      <LoaderCircle size={18} className="animate-spin text-blue-600" />
                      Analyzing procurement data...
                    </div>
                  </div>
                )}

                {chatError && <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{chatError}</div>}
                <div ref={messagesEndRef} />
              </div>

              <form onSubmit={handleSubmit} className="border-t border-slate-100 bg-white p-4 md:p-6">
                <div className="flex items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-2 focus-within:border-blue-400">
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        if (!loading) askQuestion(question)
                      }
                    }}
                    rows={2}
                    maxLength={500}
                    placeholder="Ask a procurement question..."
                    className="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-slate-400"
                  />
                  <button type="submit" disabled={loading || !question.trim()}
                    className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40">
                    <Send size={19} />
                  </button>
                </div>
                <p className="mt-3 text-center text-xs text-slate-400">
                  AI-generated answers may contain mistakes. Verify important figures.
                </p>
              </form>
            </section>
          )}
        </main>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon: Icon, subtitle, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    violet: 'bg-violet-50 text-violet-600',
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between">
        <div className={`rounded-2xl p-3 ${colors[color]}`}><Icon size={23} /></div>
        <span className="rounded-full bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500">Overview</span>
      </div>
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <h3 className="mt-2 text-3xl font-bold tracking-tight">{value}</h3>
      <p className="mt-2 text-xs text-slate-400">{subtitle}</p>
    </div>
  )
}

export default App
