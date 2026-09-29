/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        coal: {
          950: '#0B0F0E',
          900: '#111715',
          850: '#151C19',
          800: '#1A2220',
          750: '#1E2926',
          700: '#22302C',
          600: '#2A3A35',
          500: '#344740',
          400: '#4A5F58',
          300: '#6B7F78',
          200: '#9BB0A8',
          100: '#C8D5D1',
          50:  '#EBF0EE',
        },
        amber: {
          600: '#D98A00',
          500: '#F2A900',
          400: '#FFB81C',
          300: '#FFC84D',
          200: '#FFD980',
        },
        earth: {
          green:   '#2D5A3D',
          cyan:    '#1A6B7A',
          slate:   '#3A4A52',
          steel:   '#4A5568',
          graphite:'#2D3748',
        },
        status: {
          operational: '#22C55E',
          degraded:    '#F59E0B',
          offline:     '#EF4444',
          warning:     '#F97316',
        },
      },
      fontFamily: {
        sans:  ['Inter', 'system-ui', 'sans-serif'],
        mono:  ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Inter', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
        xs:    ['0.75rem', { lineHeight: '1.125rem' }],
      },
      backgroundImage: {
        'grid-coal': `linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)`,
        'topo':      `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Cpath d='M10 50 Q25 20 50 50 Q75 80 90 50' stroke='rgba(242,169,0,0.05)' fill='none' stroke-width='1'/%3E%3C/svg%3E")`,
      },
      backgroundSize: {
        'grid':  '40px 40px',
        'topo':  '100px 100px',
      },
      animation: {
        'pulse-slow':   'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow':         'glow 2s ease-in-out infinite alternate',
        'slide-in-left':'slideInLeft 0.3s ease-out',
        'fade-in':      'fadeIn 0.4s ease-out',
        'ping-slow':    'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
      },
      keyframes: {
        glow: {
          '0%':   { boxShadow: '0 0 5px rgba(242,169,0,0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(242,169,0,0.6)' },
        },
        slideInLeft: {
          '0%':   { transform: 'translateX(-100%)', opacity: 0 },
          '100%': { transform: 'translateX(0)',      opacity: 1 },
        },
        fadeIn: {
          '0%':   { opacity: 0, transform: 'translateY(8px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'coal':   '0 4px 24px rgba(0,0,0,0.6)',
        'amber':  '0 0 20px rgba(242,169,0,0.25)',
        'glow':   '0 0 30px rgba(242,169,0,0.15)',
        'panel':  '0 2px 12px rgba(0,0,0,0.5)',
        'inset-coal': 'inset 0 1px 0 rgba(255,255,255,0.05)',
      },
      borderColor: {
        DEFAULT: 'rgba(255,255,255,0.08)',
      },
    },
  },
  plugins: [],
}
