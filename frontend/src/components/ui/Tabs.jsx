export default function Tabs({ tabs = [], value, onChange }) {
  return (
    <div className="ui-tabs" role="tablist" aria-label="Tab navigation">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          role="tab"
          className={tab === value ? 'ui-tab ui-tab--active' : 'ui-tab'}
          aria-selected={tab === value}
          onClick={() => onChange(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  )
}
