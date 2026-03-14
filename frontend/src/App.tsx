import { useState } from 'react'
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
  const [people, setPeople]       = useState<Person[]>(INITIAL_PEOPLE)
  const [shifts, setShifts]       = useState<ShiftDef[]>(INITIAL_SHIFTS)
  const [assignments, setAssignments] = useState<Assignment[] | null>(null)
  const [generating, setGenerating]   = useState(false)
  const [error, setError]             = useState<string | null>(null)

  // All skills in use across people + shifts — drives autocomplete and skill chips
  const allSkills = [
    ...new Set([
      ...people.flatMap(p => p.skills),
      ...shifts.map(s => s.required_skill).filter(Boolean),
    ]),
  ]

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
    } catch {
      setError('Could not reach backend — is it running?')
    } finally {
      setGenerating(false)
    }
  }

  // Reset schedule whenever the setup changes
  function handlePeopleChange(next: React.SetStateAction<Person[]>) {
    setAssignments(null)
    setPeople(next)
  }

  function handleShiftsChange(next: React.SetStateAction<ShiftDef[]>) {
    setAssignments(null)
    setShifts(next)
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

          <button
            onClick={generate}
            disabled={generating || shifts.length === 0}
            className="w-full rounded-lg bg-slate-900 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {generating ? 'Generating…' : 'Generate Schedule'}
          </button>

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              {error}
            </p>
          )}
        </div>

        {/* Right column — schedule */}
        <div className="flex-1 min-w-0">
          <ScheduleTimeline shifts={shifts} assignments={assignments} people={people} />
        </div>
      </div>
    </div>
  )
}
