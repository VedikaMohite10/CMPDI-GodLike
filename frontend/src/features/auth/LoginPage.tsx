import React, { useState } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Zap, AlertCircle } from 'lucide-react'
import { login, getMe } from '../../api/auth'
import { useAuthStore } from '../../stores/authStore'
import type { AuthUser } from '../../types'

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})
type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const { isAuth, setAuth } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  if (isAuth) return <Navigate to="/dashboard" replace />

  const onSubmit = async (data: LoginForm) => {
    setLoading(true)
    setError(null)
    try {
      const res = await login(data.username, data.password)
      const me = await getMe(res.access_token)
      setAuth(res.access_token, me as AuthUser)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-coal-950 flex">
      {/* Left: Visual panel */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: 'url(/images/hero/coal_mine_hero.jpg)' }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-coal-950/20 to-coal-950/80" />
        <div className="absolute inset-0 bg-technical-grid opacity-20" />

        {/* Content overlay */}
        <div className="absolute bottom-16 left-10 right-10">
          <div className="h-px w-12 bg-amber-500 mb-4" />
          <h1 className="text-4xl font-black text-white mb-2 leading-tight">
            CMPDI<br />
            <span style={{ color: '#F2A900' }}>GODLIKE</span>
          </h1>
          <p className="text-coal-300 text-sm leading-relaxed max-w-xs">
            AI Mining Intelligence Platform<br />
            Central Mine Planning &amp; Design Institute Ltd.
          </p>
        </div>
      </div>

      {/* Right: Login form */}
      <div className="flex-1 lg:max-w-md flex flex-col items-center justify-center px-8 bg-coal-950">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-9 h-9 bg-amber-500 rounded-sm flex items-center justify-center">
              <span className="text-coal-950 font-black text-xs">CG</span>
            </div>
            <div>
              <div className="text-white font-bold text-base">CMPDI GODLIKE</div>
              <div className="text-amber-500 text-[10px] uppercase tracking-widest">AI Mining Intelligence</div>
            </div>
          </div>

          <div className="mb-8">
            <div className="section-label mb-2">SECURE ACCESS</div>
            <h2 className="text-xl font-bold text-white">Sign in to continue</h2>
            <p className="text-coal-400 text-xs mt-1">
              Enterprise credentials required. Contact your administrator for access.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Username */}
            <div>
              <label className="section-label block mb-1.5">USERNAME</label>
              <input
                {...register('username')}
                type="text"
                autoComplete="username"
                className="industrial-input"
                placeholder="Enter username"
              />
              {errors.username && (
                <p className="text-status-offline text-xs mt-1">{errors.username.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="section-label block mb-1.5">PASSWORD</label>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="industrial-input pr-10"
                  placeholder="Enter password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-coal-400 hover:text-white"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-status-offline text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-sm p-3">
                <AlertCircle size={14} className="text-status-offline shrink-0" />
                <span className="text-status-offline text-xs">{error}</span>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-2.5 mt-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 rounded-full border-2 border-coal-950/30 border-t-coal-950 animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  <Zap size={14} />
                  Access Platform
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-[10px] text-coal-600 leading-relaxed">
              Secure access to CMPDI enterprise intelligence.<br />
              Unauthorized access is prohibited and subject to legal action.<br />
              Government of India · Ministry of Coal · CMPDI
            </p>
          </div>

          <div className="mt-4 text-center">
            <Link to="/" className="text-coal-400 text-xs hover:text-white transition-colors">
              ← Back to Platform Overview
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
