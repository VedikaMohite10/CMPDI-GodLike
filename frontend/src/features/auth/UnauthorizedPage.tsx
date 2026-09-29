import React from 'react'
import { Link } from 'react-router-dom'
import { ShieldOff, ArrowLeft } from 'lucide-react'

export default function UnauthorizedPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-24 text-center px-8">
      <ShieldOff size={40} className="text-coal-600 mb-4" />
      <h1 className="text-xl font-bold text-white mb-2">Access Denied</h1>
      <p className="text-coal-400 text-sm max-w-sm mb-6">
        You do not have the required permissions to view this page.
        Contact your administrator to request access.
      </p>
      <Link to="/dashboard" className="btn-secondary flex items-center gap-2">
        <ArrowLeft size={14} /> Return to Dashboard
      </Link>
    </div>
  )
}
