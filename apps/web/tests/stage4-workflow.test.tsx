import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FieldCard, PartyCard, TasksPage } from '@/components/casepilot-app'
import type { ReviewField, ReviewParty, ReviewTask } from '@/lib/api'

const citation = { document_id: 'doc-1', document_name: 'evidence.txt', passage_id: 'passage-1', passage_label: 'Passage 1', page_number: null, quote: 'Buyer Rao paid INR 500000.' }

const field: ReviewField = { id: 'field-1', field_key: 'payment', label: 'Payment', suggested_value: 'INR 500000', reviewed_value: null, value: 'INR 500000', status: 'pending', reviewed_at: null, citations: [citation] }
const party: ReviewParty = { id: 'party-1', suggested_name: 'Rao', suggested_role: 'Buyer', reviewed_name: null, reviewed_role: null, name: 'Rao', role: 'Buyer', status: 'pending', reviewed_at: null, citations: [citation] }
const tasks: ReviewTask[] = [
  { id: 'ai-1', source: 'ai', title: 'Request receipt', description: 'Request payment receipt.', status: 'proposed', finding_id: null, created_at: '2026-09-27T00:00:00Z', updated_at: '2026-09-27T00:00:00Z', citations: [citation] },
  { id: 'manual-1', source: 'manual', title: 'Call buyer', description: 'Clarify possession.', status: 'approved', finding_id: null, created_at: '2026-09-27T00:00:00Z', updated_at: '2026-09-27T00:00:00Z', citations: [] },
]

describe('Stage 4 review workflow UI', () => {
  it('sends a field confirmation and retains its cited AI suggestion', () => {
    const onAction = vi.fn().mockResolvedValue(undefined)
    render(<FieldCard caseId="case-1" item={field} onAction={onAction} busy={false} />)
    expect(screen.getByText('AI suggestion: INR 500000')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(onAction).toHaveBeenCalledWith('field-1', { action: 'confirm' })
    expect(screen.getByText('evidence.txt · Passage 1')).toBeTruthy()
  })

  it('opens party edit with a separate lawyer replacement', () => {
    const onAction = vi.fn().mockResolvedValue(undefined)
    render(<PartyCard caseId="case-1" item={party} onAction={onAction} busy={false} />)
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    const role = screen.getByDisplayValue('Buyer')
    fireEvent.change(role, { target: { value: 'Purchaser' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save review' }))
    expect(onAction).toHaveBeenCalledWith('party-1', { action: 'edit', name: 'Rao', role: 'Purchaser' })
  })

  it('groups AI and manual tasks and emits the allowed operations', () => {
    const onCreate = vi.fn().mockResolvedValue(undefined)
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    render(<TasksPage caseId="case-1" tasks={tasks} onCreate={onCreate} onUpdate={onUpdate} busy={false} />)
    expect(screen.getByText('AI-proposed')).toBeTruthy()
    expect(screen.getByText('Manual')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(onUpdate).toHaveBeenCalledWith('ai-1', { status: 'approved' })
    fireEvent.click(screen.getByRole('button', { name: 'Mark done' }))
    expect(onUpdate).toHaveBeenCalledWith('manual-1', { status: 'done' })
    fireEvent.change(screen.getByPlaceholderText('Task title'), { target: { value: 'Get keys' } })
    fireEvent.change(screen.getByPlaceholderText('Describe the follow-up work'), { target: { value: 'Ask for signed handover record.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))
    expect(onCreate).toHaveBeenCalledWith({ title: 'Get keys', description: 'Ask for signed handover record.' })
  })
})
