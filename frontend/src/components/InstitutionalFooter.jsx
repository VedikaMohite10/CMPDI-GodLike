import React from 'react'

export default function InstitutionalFooter() {
  return (
    <footer className="landing-footer">
      <div className="landing-shell landing-footer__inner">
        <div className="landing-footer-brand-block">
          <div className="landing-footer-brand">COAL INDIA LIMITED • CMPDI</div>
          <div className="landing-footer-text">
            A Maharatna Company — Central Mine Planning &amp; Design Institute. Building a Sustainable Mining Future.
          </div>
        </div>

        <div className="landing-footer-meta" style={{ flexDirection: 'row', gap: '20px', alignItems: 'center' }}>
          <a href="#about" style={{ color: 'rgba(255,255,255,0.72)', textDecoration: 'none' }}>About</a>
          <a href="#contact" style={{ color: 'rgba(255,255,255,0.72)', textDecoration: 'none' }}>Contact</a>
          <a href="#help" style={{ color: 'rgba(255,255,255,0.72)', textDecoration: 'none' }}>Help</a>
          <a href="#privacy" style={{ color: 'rgba(255,255,255,0.72)', textDecoration: 'none' }}>Privacy</a>
          <a href="#terms" style={{ color: 'rgba(255,255,255,0.72)', textDecoration: 'none' }}>Terms</a>
          <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: '12px' }}>
            © {new Date().getFullYear()} CMPDI. All rights reserved.
          </span>
        </div>
      </div>
    </footer>
  )
}
