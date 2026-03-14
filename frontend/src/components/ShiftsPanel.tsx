import type { ShiftDef } from '@/types'

interface RowProps {
  shift: ShiftDef
  allSkills: string[]
  onChange: (s: ShiftDef) => void
  onRemove: () => void
}

function ShiftRow({ shift, allSkills, onChange, onRemove }: RowProps) {
  return (
    <div className="py-3">
      <div className="flex items-center gap-2">
        <input
          value={shift.name}
          onChange={e => onChange({ ...shift, name: e.target.value })}
          className="flex-1 text-sm font-medium text-slate-800 bg-transparent border-b border-transparent hover:border-slate-200 focus:border-slate-400 focus:outline-none pb-0.5"
        />
        <button
          onClick={onRemove}
          className="text-slate-300 hover:text-red-400 text-lg leading-none transition-colors"
        >
          ×
        </button>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input
          type="date"
          value={shift.date}
          onChange={e => onChange({ ...shift, date: e.target.value })}
          className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 focus:border-slate-400 focus:outline-none"
        />
        <input
          type="time"
          value={shift.start}
          onChange={e => onChange({ ...shift, start: e.target.value })}
          className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 focus:border-slate-400 focus:outline-none"
        />
        <span className="text-xs text-slate-300">→</span>
        <input
          type="time"
          value={shift.end}
          onChange={e => onChange({ ...shift, end: e.target.value })}
          className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 focus:border-slate-400 focus:outline-none"
        />

        {/* Required skill — datalist allows free-text + autocomplete */}
        <input
          list={`skills-${shift.id}`}
          value={shift.required_skill}
          onChange={e => onChange({ ...shift, required_skill: e.target.value })}
          placeholder="skill"
          className="w-28 rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 focus:border-slate-400 focus:outline-none"
        />
        <datalist id={`skills-${shift.id}`}>
          {allSkills.map(s => <option key={s} value={s} />)}
        </datalist>

        <span className="text-xs text-slate-400">×</span>
        <input
          type="number"
          min={1}
          max={20}
          value={shift.required_count}
          onChange={e => onChange({ ...shift, required_count: Math.max(1, parseInt(e.target.value) || 1) })}
          className="w-10 rounded border border-slate-200 px-2 py-1 text-center text-xs text-slate-600 focus:border-slate-400 focus:outline-none"
        />
        <span className="text-xs text-slate-400">person{shift.required_count !== 1 ? 's' : ''}</span>
      </div>
    </div>
  )
}

interface Props {
  shifts: ShiftDef[]
  setShifts: React.Dispatch<React.SetStateAction<ShiftDef[]>>
  allSkills: string[]
}

export function ShiftsPanel({ shifts, setShifts, allSkills }: Props) {
  function add() {
    setShifts(prev => [
      ...prev,
      {
        id: `s${Date.now()}`,
        name: 'New Shift',
        start: '08:00',
        end: '11:00',
        required_skill: allSkills[0] ?? '',
        required_count: 1,
        date: new Date().toISOString().split('T')[0],
      },
    ])
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Shifts</h2>
        <button onClick={add} className="text-xs font-medium text-slate-400 hover:text-slate-700 transition-colors">
          + Add shift
        </button>
      </div>
      <div className="divide-y divide-slate-100">
        {shifts.length === 0 && (
          <p className="py-4 text-center text-xs text-slate-400">No shifts yet.</p>
        )}
        {shifts.map(s => (
          <ShiftRow
            key={s.id}
            shift={s}
            allSkills={allSkills}
            onChange={updated => setShifts(prev => prev.map(x => x.id === s.id ? updated : x))}
            onRemove={() => setShifts(prev => prev.filter(x => x.id !== s.id))}
          />
        ))}
      </div>
    </section>
  )
}
