import { useState } from 'react'
import type { Person, ShiftDef, Assignment } from '@/types'

type AssignmentMap = Record<string, Assignment[]>

const SKILL_PALETTE: Record<string, { block: string; label: string; badge: string }> = {
  physio:       { block: 'border-violet-200 bg-violet-50',  label: 'text-violet-800', badge: 'bg-violet-100 text-violet-700' },
  shift_leader: { block: 'border-blue-200 bg-blue-50',      label: 'text-blue-800',   badge: 'bg-blue-100 text-blue-700'   },
  medic:        { block: 'border-emerald-200 bg-emerald-50', label: 'text-emerald-800', badge: 'bg-emerald-100 text-emerald-700' },
}

const FALLBACK = { block: 'border-slate-200 bg-slate-50', label: 'text-slate-700', badge: 'bg-slate-100 text-slate-600' }

function palette(skill: string) { return SKILL_PALETTE[skill] ?? FALLBACK }
function timeToMin(t: string): number { const [h, m] = t.split(':').map(Number); return h * 60 + m }

const HOUR_PX = 72

interface Props {
  shifts: ShiftDef[]
  assignmentMap: AssignmentMap
  people: Person[]
  selectedDate: string
  onDateChange: (date: string) => void
}

function DayColumn({ shifts, assignments, people }: { shifts: ShiftDef[]; assignments: Assignment[] | null; people: Person[] }) {
  const personById = Object.fromEntries(people.map(p => [p.id, p]))
  const assignmentByShift = Object.fromEntries((assignments ?? []).map(a => [a.shift_id, a]))

  if (shifts.length === 0) return (
    <div className="flex h-24 items-center justify-center text-xs text-slate-400">No shifts</div>
  )

  const allMins = shifts.flatMap(s => [timeToMin(s.start), timeToMin(s.end)])
  const minMin = Math.floor((Math.min(...allMins) - 30) / 60) * 60
  const maxMin = Math.ceil((Math.max(...allMins) + 30) / 60) * 60
  const totalHeight = ((maxMin - minMin) / 60) * HOUR_PX

  const hours: number[] = []
  for (let t = minMin; t <= maxMin; t += 60) hours.push(t)
  function top(min: number) { return ((min - minMin) / 60) * HOUR_PX }

  const columns: Array<{ shift: ShiftDef; col: number; totalCols: number }> = []
  shifts.forEach(shift => {
    const sMin = timeToMin(shift.start)
    const eMin = timeToMin(shift.end)
    const overlapping = columns.filter(c => sMin < timeToMin(c.shift.end) && eMin > timeToMin(c.shift.start))
    const usedCols = overlapping.map(c => c.col)
    let col = 0
    while (usedCols.includes(col)) col++
    columns.push({ shift, col, totalCols: 0 })
  })
  columns.forEach(c => {
    const overlapping = columns.filter(o => timeToMin(c.shift.start) < timeToMin(o.shift.end) && timeToMin(c.shift.end) > timeToMin(o.shift.start))
    c.totalCols = Math.max(...overlapping.map(o => o.col)) + 1
  })
  const colMap = Object.fromEntries(columns.map(c => [c.shift.id, c]))

  return (
    <div className="flex gap-2">
      <div className="relative w-10 flex-shrink-0 select-none" style={{ height: totalHeight }}>
        {hours.map(t => (
          <div key={t} className="absolute right-0 -translate-y-2 text-right text-xs text-slate-400" style={{ top: top(t) }}>
            {String(Math.floor(t / 60)).padStart(2, '0')}:00
          </div>
        ))}
      </div>
      <div className="relative flex-1" style={{ height: totalHeight }}>
        {hours.map(t => (
          <div key={t} className="absolute w-full border-t border-slate-100" style={{ top: top(t) }} />
        ))}
        {shifts.map(shift => {
          const sMin = timeToMin(shift.start)
          const eMin = timeToMin(shift.end)
          const blockTop = top(sMin)
          const blockH = top(eMin) - blockTop
          const pal = palette(shift.required_skill)
          const a = assignmentByShift[shift.id]
          const assigned = a?.person_ids.map(id => personById[id]).filter(Boolean) ?? []
          const unfulfilled = a && !a.fulfilled
          const col = colMap[shift.id].col
          const totalCols = colMap[shift.id].totalCols
          return (
            <div
              key={shift.id}
              className={`absolute rounded-lg border px-2 py-1 ${pal.block} ${!a ? 'border-dashed opacity-60' : ''}`}
              style={{ top: blockTop + 2, height: blockH - 4, left: `${(col / totalCols) * 100}%`, width: `${(1 / totalCols) * 100}%` }}
            >
              <div className={`text-xs font-semibold ${pal.label}`}>{shift.name}</div>
              <div className={`text-xs opacity-70 ${pal.label}`}>{shift.start}–{shift.end}</div>
              {a && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {unfulfilled && <span className="rounded bg-red-100 px-1 py-0.5 text-xs text-red-700">⚠ Unfulfilled</span>}
                  {assigned.map(p => (
                    <span key={p.id} className={`rounded px-1 py-0.5 text-xs font-medium ${pal.badge}`}>{p.name}</span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function ScheduleTimeline({ shifts, assignmentMap, people, selectedDate, onDateChange }: Props) {
  const [view, setView] = useState<'day' | 'week'>('day')

  const allDates = [...new Set(shifts.map(s => s.date).filter(Boolean))].sort() as string[]

  if (shifts.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white text-sm text-slate-400">
        Add shifts on the left to get started.
      </div>
    )
  }

  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })

  function prevDay() {
    const idx = allDates.indexOf(selectedDate)
    if (idx > 0) onDateChange(allDates[idx - 1])
  }
  function nextDay() {
    const idx = allDates.indexOf(selectedDate)
    if (idx < allDates.length - 1) onDateChange(allDates[idx + 1])
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Generated Schedule</h2>
        <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
          <button onClick={() => setView('day')} className={`px-3 py-1 ${view === 'day' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>Day</button>
          <button onClick={() => setView('week')} className={`px-3 py-1 ${view === 'week' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>Week</button>
        </div>
      </div>
      {allDates.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {allDates.map(d => (
            <button
              key={d}
              onClick={() => { onDateChange(d); setView('day') }}
              className={`rounded px-2 py-1 text-xs font-medium ${selectedDate === d ? 'bg-slate-900 text-white' : 'border border-slate-200 text-slate-600 hover:bg-slate-100'}`}
            >
              {new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
              {assignmentMap[d] ? ' ✓' : ''}
            </button>
          ))}
        </div>
      )}

      {view === 'day' && (
        <>
          <div className="mb-3 flex items-center justify-between">
            <button onClick={prevDay} disabled={allDates.indexOf(selectedDate) <= 0} className="rounded px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 disabled:opacity-30">←</button>
            <span className="text-sm font-medium text-slate-700">{formatDate(selectedDate)}</span>
            <button onClick={nextDay} disabled={allDates.indexOf(selectedDate) >= allDates.length - 1} className="rounded px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 disabled:opacity-30">→</button>
          </div>
          <DayColumn shifts={shifts.filter(s => s.date === selectedDate)} assignments={assignmentMap[selectedDate] ?? null} people={people} />
        </>
      )}

      {view === 'week' && (
        <div className="flex gap-2 overflow-x-auto">
          {allDates.length > 0 ? allDates.map(date => (
            <div key={date} className="min-w-0 flex-1 cursor-pointer" style={{ minWidth: 140 }} onClick={() => { onDateChange(date); setView('day') }}>
              <div className={`mb-2 text-center text-xs font-medium rounded px-1 py-0.5 ${date === selectedDate ? 'bg-slate-900 text-white' : 'text-slate-500'}`}>
                {formatDate(date)}
                {assignmentMap[date] ? ' ✓' : ''}
              </div>
              <DayColumn shifts={shifts.filter(s => s.date === date)} assignments={assignmentMap[date] ?? null} people={people} />
            </div>
          )) : (
            <DayColumn shifts={shifts} assignments={assignmentMap[selectedDate] ?? null} people={people} />
          )}
        </div>
      )}
    </div>
  )
}
