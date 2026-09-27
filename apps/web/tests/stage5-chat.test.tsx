import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChatPage } from '@/components/casepilot-app'
import type { ChatExchange, ChatMessage } from '@/lib/api'

const citation = { document_id: 'doc-1', document_name: 'receipt.txt', passage_id: 'passage-1', passage_label: 'Passage 1', page_number: null, quote: 'Buyer Rao paid INR 500000.' }
const history: ChatMessage[] = [
  { id: 'u-1', exchange_id: 'x-1', role: 'user', content: 'What payment is recorded?', response_type: null, citations: [], created_at: '2026-09-27T00:00:00Z' },
  { id: 'a-1', exchange_id: 'x-1', role: 'assistant', content: 'The evidence records INR 500000.', response_type: 'evidence', citations: [citation], created_at: '2026-09-27T00:00:01Z' },
]

function exchange(question: string): ChatExchange {
  return {
    user_message: { ...history[0], id: 'u-2', exchange_id: 'x-2', content: question },
    assistant_message: { ...history[1], id: 'a-2', exchange_id: 'x-2', response_type: 'general_guidance', content: 'General guidance — not based on case documents. This was not found in uploaded material.', citations: [] },
  }
}

describe('Stage 5 case chat', () => {
  it('renders persisted evidence history and citation navigation', () => {
    render(<ChatPage caseId="case-1" messages={history} onSend={vi.fn()} />)
    expect(screen.getByText('Evidence-based')).toBeTruthy()
    const link = screen.getByRole('link', { name: /receipt.txt/ })
    expect(link.getAttribute('href')).toBe('/cases/case-1/documents?document=doc-1&passage=passage-1')
  })

  it('shows a pending question, disables duplicate sends, and renders guidance after success', async () => {
    let resolve!: (value: ChatExchange) => void
    const onSend = vi.fn(() => new Promise<ChatExchange>(done => { resolve = done }))
    const view = render(<ChatPage caseId="case-1" messages={[]} onSend={onSend} />)
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'What law applies?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(screen.getByText('What law applies?')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Sending…' }) as HTMLButtonElement).disabled).toBe(true)
    resolve(exchange('What law applies?'))
    await waitFor(() => expect(onSend).toHaveBeenCalledTimes(1))
    view.rerender(<ChatPage caseId="case-1" messages={[exchange('What law applies?').user_message, exchange('What law applies?').assistant_message]} onSend={onSend} />)
    expect(screen.getByText('General guidance')).toBeTruthy()
  })

  it('restores the failed question and removes the temporary message', async () => {
    const onSend = vi.fn().mockRejectedValue(new Error('The AI provider is temporarily unavailable.'))
    render(<ChatPage caseId="case-1" messages={[]} onSend={onSend} />)
    fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'Retry this question' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await screen.findByText(/Your question was restored/)
    expect((screen.getByLabelText('Question') as HTMLTextAreaElement).value).toBe('Retry this question')
    expect(screen.queryByText('Sending…')).toBeNull()
  })
})
