import { describe, expect, it } from 'vitest'
import { evidenceHref, type Citation } from '@/lib/api'

describe('evidenceHref', () => {
  it('keeps document and stable passage identifiers in the Documents route', () => {
    const citation: Citation = { document_id: 'doc id', document_name: 'notice.pdf', passage_id: 'passage id', passage_label: 'Page 2, Passage 1', page_number: 2, quote: 'Quoted text' }
    expect(evidenceHref('case-1', citation)).toBe('/cases/case-1/documents?document=doc id&passage=passage id')
  })
})
