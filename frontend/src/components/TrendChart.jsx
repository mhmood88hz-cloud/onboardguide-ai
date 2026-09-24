import { useState } from 'react';

const WIDTH = 320;
const HEIGHT = 120;
const PADDING = 16;

/**
 * Leichtgewichtiges Liniendiagramm (reines SVG, keine Chart-Library) für eine einzelne
 * Zeitreihe — gleiches visuelles Muster wie LeadSpeak AIs TrendChart-Komponente:
 * Hairline-Gridlines, Endpunkt mit Ring, Crosshair + Tooltip beim Hover.
 */
export default function TrendChart({ title, points, unit = '', color = '#edb268' }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (!points || points.length === 0) {
    return (
      <div style={s.card}>
        <p style={s.title}>{title}</p>
        <p style={s.empty}>Noch nicht genug Daten.</p>
      </div>
    );
  }

  const values = points.map(p => p.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const range = max - min || 1;

  const xStep = points.length > 1 ? (WIDTH - PADDING * 2) / (points.length - 1) : 0;
  const coords = points.map((p, i) => ({
    x: points.length > 1 ? PADDING + i * xStep : WIDTH / 2,
    y: PADDING + (1 - (p.value - min) / range) * (HEIGHT - PADDING * 2),
  }));

  const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x},${c.y}`).join(' ');
  const last = coords[coords.length - 1];
  const hovered = hoverIndex !== null ? points[hoverIndex] : null;
  const hoveredCoord = hoverIndex !== null ? coords[hoverIndex] : null;

  const handleMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const relX = ((event.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let nearestDist = Infinity;
    coords.forEach((c, i) => {
      const dist = Math.abs(c.x - relX);
      if (dist < nearestDist) { nearestDist = dist; nearest = i; }
    });
    setHoverIndex(nearest);
  };

  return (
    <div style={s.card}>
      <div style={s.header}>
        <p style={s.title}>{title}</p>
        <p style={s.value}>{points[points.length - 1].value}{unit}</p>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        style={{ width: '100%', marginTop: '12px' }}
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        {[0.25, 0.5, 0.75].map(f => (
          <line key={f}
                x1={PADDING} x2={WIDTH - PADDING}
                y1={PADDING + f * (HEIGHT - PADDING * 2)} y2={PADDING + f * (HEIGHT - PADDING * 2)}
                stroke="#26343f" strokeWidth={1} />
        ))}
        <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        {hoveredCoord && (
          <line x1={hoveredCoord.x} x2={hoveredCoord.x} y1={PADDING} y2={HEIGHT - PADDING}
                stroke="#26343f" strokeWidth={1} />
        )}
        <circle cx={last.x} cy={last.y} r={4} fill={color} stroke="#141e29" strokeWidth={2} />
        {hoveredCoord && hoverIndex !== coords.length - 1 && (
          <circle cx={hoveredCoord.x} cy={hoveredCoord.y} r={4} fill={color} stroke="#141e29" strokeWidth={2} />
        )}
      </svg>
      <p style={s.tooltip}>
        {hovered
          ? `${new Date(hovered.date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })}: ${hovered.value}${unit}`
          : ''}
      </p>
    </div>
  );
}

const s = {
  card:    { borderRadius: '16px', padding: '20px', background: 'transparent' },
  header:  { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' },
  title:   { color: '#eef3f7', fontSize: '14px', fontWeight: '600', margin: 0 },
  value:   { color: '#eef3f7', fontSize: '18px', fontWeight: '700', margin: 0 },
  empty:   { color: '#8fa1ae', fontSize: '12px', textAlign: 'center', marginTop: '32px' },
  tooltip: { color: '#8fa1ae', fontSize: '12px', textAlign: 'center', height: '16px', margin: '4px 0 0' },
};
