import { useState } from 'react'
import jsPDF from 'jspdf'
import type { Person, ShiftDef, Assignment } from '@/types'
import { PeoplePanel } from '@/components/PeoplePanel'
import { ShiftsPanel } from '@/components/ShiftsPanel'
import { ScheduleTimeline } from '@/components/ScheduleTimeline'

const TODAY = new Date().toISOString().split('T')[0]

const INITIAL_PEOPLE: Person[] = [
  { id: 'p1', name: 'Alice',  skills: ['physio'],       availability: { '00:00-23:59': 'expected' }, max_hours_per_day: 8, min_rest_minutes: 30 },
  { id: 'p2', name: 'Bob',    skills: ['shift_leader'], availability: { '00:00-23:59': 'expected' }, max_hours_per_day: 8, min_rest_minutes: 30 },
  { id: 'p3', name: 'Carol',  skills: ['medic'],        availability: { '00:00-23:59': 'expected' }, max_hours_per_day: 8, min_rest_minutes: 30 },
]

const INITIAL_SHIFTS: ShiftDef[] = [
  { id: 's1', name: 'Physio Session', start: '08:00', end: '11:00', required_skill: 'physio',       required_count: 1, date: TODAY },
  { id: 's2', name: 'General Ward',   start: '11:00', end: '14:00', required_skill: 'shift_leader', required_count: 1, date: TODAY },
  { id: 's3', name: 'Medical Bay',    start: '14:00', end: '17:00', required_skill: 'medic',        required_count: 1, date: TODAY },
]

export default function App() {
  const [people, setPeople]       = useState<Person[]>(() => {
    try { const s = localStorage.getItem('sp_people'); return s ? JSON.parse(s) : INITIAL_PEOPLE } catch { return INITIAL_PEOPLE }
  })
  const [shifts, setShifts]       = useState<ShiftDef[]>(() => {
    try { const s = localStorage.getItem('sp_shifts'); return s ? JSON.parse(s) : INITIAL_SHIFTS } catch { return INITIAL_SHIFTS }
  })
  const [assignments, setAssignments] = useState<Assignment[] | null>(() => {
    try { const s = localStorage.getItem('sp_assignments'); return s ? JSON.parse(s) : null } catch { return null }
  })
  const [generating, setGenerating]   = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [refineInput, setRefineInput] = useState('')
  const [refining, setRefining]       = useState(false)
  const [explanation, setExplanation] = useState<string | null>(null)

  // All skills in use across people + shifts — drives autocomplete and skill chips
  const allSkills = [
    ...new Set([
      ...people.flatMap(p => p.skills),
      ...shifts.map(s => s.required_skill).filter(Boolean),
    ]),
  ]

  function exportPDF() {
    const pdf = new jsPDF({ orientation: 'landscape' })
    const pageW = pdf.internal.pageSize.getWidth()
    const date = new Date().toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

    // Header
    pdf.setFillColor(30, 30, 30)
    pdf.rect(0, 0, pageW, 20, 'F')
    pdf.setTextColor(255, 255, 255)
    pdf.setFontSize(14)
    pdf.setFont('helvetica', 'bold')
    pdf.text('ShiftPlanner', 14, 13)
    pdf.setFontSize(10)
    pdf.setFont('helvetica', 'normal')
    pdf.text(date, pageW - 14, 13, { align: 'right' })

    // Table header
    pdf.setTextColor(0, 0, 0)
    pdf.setFillColor(240, 240, 240)
    pdf.rect(10, 25, pageW - 20, 8, 'F')
    pdf.setFont('helvetica', 'bold')
    pdf.setFontSize(9)
    pdf.text('Shift', 14, 31)
    pdf.text('Time', 70, 31)
    pdf.text('Skill', 110, 31)
    pdf.text('Assigned', 150, 31)
    pdf.text('Status', 230, 31)

    // Table rows
    pdf.setFont('helvetica', 'normal')
    let y = 42
    shifts.forEach((shift, i) => {
      if (i % 2 === 0) {
        pdf.setFillColor(250, 250, 250)
        pdf.rect(10, y - 5, pageW - 20, 8, 'F')
      }
      const a = assignments?.find(x => x.shift_id === shift.id)
      const names = a?.person_ids.map(id => people.find(p => p.id === id)?.name ?? id).join(', ') ?? '-'
      const status = !a ? 'No schedule' : a.fulfilled ? 'Fulfilled' : 'Unfulfilled'
      pdf.setTextColor(0, 0, 0)
      pdf.text(shift.name, 14, y)
      pdf.text(`${shift.start} - ${shift.end}`, 70, y)
      pdf.text(shift.required_skill, 110, y)
      pdf.text(names, 150, y)
      if (!a || !a.fulfilled) pdf.setTextColor(200, 50, 50)
      else pdf.setTextColor(50, 150, 50)
      pdf.text(status, 230, y)
      pdf.setTextColor(0, 0, 0)
      y += 9
    })

    // Border
    pdf.setDrawColor(200, 200, 200)
    pdf.rect(10, 25, pageW - 20, y - 25)

    pdf.save('schedule.pdf')
  }

  function reset() {
    if (!window.confirm('Clear the generated schedule? People and shifts will be kept.')) return
    localStorage.removeItem('sp_assignments')
    setAssignments(null)
    setError(null)
    setExplanation(null)
  }

  async function generate() {
    setGenerating(true)
    setError(null)
    setAssignments(null)
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ people, shifts }),
      })
      const data = await res.json()
      setAssignments(data.assignments)
      localStorage.setItem('sp_assignments', JSON.stringify(data.assignments))
    } catch {
      setError('Could not reach backend — is it running?')
    } finally {
      setGenerating(false)
    }
  }

  async function refine() {
    if (!assignments || !refineInput.trim()) return
    setRefining(true)
    setError(null)
    setExplanation(null)
    try {
      const res = await fetch('/api/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: refineInput, current_schedule: assignments, people: people }),
      })
      const data = await res.json()
      setAssignments(data.updated_schedule)
      localStorage.setItem('sp_assignments', JSON.stringify(data.updated_schedule))
      setExplanation(data.explanation ?? null)
    } catch {
      setError('Refine request failed — is the backend running?')
    } finally {
      setRefining(false)
    }
  }

  // Reset schedule whenever the setup changes
  function handlePeopleChange(next: React.SetStateAction<Person[]>) {
    setAssignments(null)
    localStorage.removeItem('sp_assignments')
    setPeople(prev => {
      const val = typeof next === 'function' ? next(prev) : next
      localStorage.setItem('sp_people', JSON.stringify(val))
      return val
    })
  }

  function handleShiftsChange(next: React.SetStateAction<ShiftDef[]>) {
    setAssignments(null)
    localStorage.removeItem('sp_assignments')
    setShifts(prev => {
      const val = typeof next === 'function' ? next(prev) : next
      localStorage.setItem('sp_shifts', JSON.stringify(val))
      return val
    })
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-lg font-bold text-slate-900">ShiftPlanner</h1>
        <p className="text-xs text-slate-400">Monday 3 March 2026</p>
      </header>

      <div className="mx-auto max-w-screen-lg px-6 py-6 flex gap-5">
        {/* Left column — setup */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-4">
          <PeoplePanel people={people} setPeople={handlePeopleChange} allSkills={allSkills} />
          <ShiftsPanel shifts={shifts} setShifts={handleShiftsChange} allSkills={allSkills} />

          <div className="flex gap-2">
            <button
              onClick={generate}
              disabled={generating || shifts.length === 0}
              className="flex-1 rounded-lg bg-slate-900 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {generating ? 'Generating…' : 'Generate Schedule'}
            </button>
            <button
              onClick={reset}
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100"
            >
              Reset
            </button>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={refineInput}
              onChange={e => setRefineInput(e.target.value)}
              placeholder="e.g. Remove Alice from the morning shift"
              className="flex-1 min-w-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
            <button
              onClick={refine}
              disabled={refining || !assignments?.length || !refineInput.trim()}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {refining ? 'Refining…' : 'Refine'}
            </button>
          </div>

          {explanation && (
            <p className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              {explanation}
            </p>
          )}

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              {error}
            </p>
          )}
        </div>

        {/* Right column — schedule */}
        <div className="flex-1 min-w-0">
          <div id="schedule-timeline">
            <ScheduleTimeline shifts={shifts} assignments={assignments} people={people} />
          </div>
          {assignments && (
            <button
              onClick={exportPDF}
              className="mt-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100"
            >
              Export PDF
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
