'use client'

import { useEffect, useState } from 'react'
import DOMPurify from 'dompurify'
import mammoth from 'mammoth'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'
import 'react-pdf/dist/Page/AnnotationLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

type Props = { fileName: string; contentType: string; readUrl: string; onRefresh: () => void }

export function DocumentPreview({ fileName, contentType, readUrl, onRefresh }: Props) {
  const [pdfPages, setPdfPages] = useState<number | null>(null)
  const [docx, setDocx] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!contentType.includes('wordprocessingml')) return
    let active = true
    setDocx(null); setError(null)
    void fetch(readUrl).then(async response => {
      if (!response.ok) throw new Error('The temporary document link has expired.')
      return mammoth.convertToHtml({ arrayBuffer: await response.arrayBuffer() })
    }).then(result => { if (active) setDocx(DOMPurify.sanitize(result.value)) }).catch(() => { if (active) setError('The DOCX preview could not be prepared. Refresh the document link and try again.') })
    return () => { active = false }
  }, [contentType, readUrl])
  if (contentType === 'application/pdf') return <section className="min-h-[700px] overflow-auto bg-[#F7F8FA] p-6"><Document file={readUrl} loading={<p className="text-sm">Loading PDF…</p>} error={<PreviewError onRefresh={onRefresh} />} onLoadSuccess={({ numPages }) => setPdfPages(numPages)}>{pdfPages && Array.from({ length: pdfPages }, (_, index) => <div key={index} className="mb-5"><Page pageNumber={index + 1} width={850} /></div>)}</Document></section>
  if (error) return <PreviewError onRefresh={onRefresh} />
  if (!docx) return <p className="p-6 text-sm text-[#525252]">Preparing DOCX preview…</p>
  return <article aria-label={`${fileName} preview`} className="prose max-w-none p-6" dangerouslySetInnerHTML={{ __html: docx }} />
}
function PreviewError({ onRefresh }: { onRefresh: () => void }) { return <div className="p-6 text-sm text-[#991B1B]">The document preview is unavailable. <button onClick={onRefresh} className="font-semibold underline">Refresh preview</button></div> }
