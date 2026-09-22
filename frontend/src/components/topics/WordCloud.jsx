export default function WordCloud({ items = [] }) {
  const width = 600
  const height = 220
  const placedItems = []

  const packedItems = items.map((item) => {
    const size = Math.min(Math.max(16 + item.value * 0.22, 16), 32)
    const x = width / 2
    const y = height / 2
    return { ...item, size, x, y }
  })

  packedItems.forEach((item) => {
    let angle = 0
    let radius = 12
    let placed = false

    while (angle < Math.PI * 2 * 6 && !placed) {
      const candidateX = width / 2 + Math.cos(angle) * radius
      const candidateY = height / 2 + Math.sin(angle) * radius
      const fits = packedItems.every((other) => {
        if (other === item) {
          return true
        }

        const dx = candidateX - other.x
        const dy = candidateY - other.y
        const distance = Math.hypot(dx, dy)
        return distance > Math.max(item.size, other.size) * 0.7
      })

      if (
        fits &&
        candidateX - item.size / 2 > 10 &&
        candidateX + item.size / 2 < width - 10 &&
        candidateY - item.size / 2 > 10 &&
        candidateY + item.size / 2 < height - 10
      ) {
        item.x = candidateX
        item.y = candidateY
        placed = true
      }

      angle += 0.38
      radius += 8
    }

    if (!placed) {
      item.x = item.size * 1.2 + (placedItems.length % 5) * 18
      item.y = height * 0.5 + ((placedItems.length % 6) - 2.5) * 18
    }

    placedItems.push(item)
  })

  return (
    <div className="word-cloud" style={{ position: 'relative', width: '100%', height: '220px' }}>
      {packedItems.map((item) => (
        <span
          key={item.label}
          className={`word-cloud__item word-cloud__item--${item.tone || 'steel'}`}
          style={{
            position: 'absolute',
            left: `${item.x}px`,
            top: `${item.y}px`,
            fontSize: `${item.size}px`,
            transform: 'translate(-50%, -50%)',
          }}
        >
          {item.label}
        </span>
      ))}
    </div>
  )
}
