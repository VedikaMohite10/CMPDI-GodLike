import axios from 'axios'
import { API_BASE_URL } from '../app/config'

// Separate raw axios for auth (no circular dependency with store)
const authAxios = axios.create({ baseURL: API_BASE_URL, timeout: 15000 })

export interface LoginResponse {
  access_token: string
  token_type:   string
  expires_in_minutes: number
  username: string
  role: string
}

export interface UserOut {
  id:        string
  username:  string
  role:      string
  is_active: boolean
}

export interface CreateUserRequest {
  username: string
  password: string
  role:     'analyst' | 'reviewer' | 'admin'
}

export interface UpdateUserRequest {
  role?:      string
  is_active?: boolean
}

// POST /auth/login  (form-encoded)
export async function login(username: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)

  const { data } = await authAxios.post<LoginResponse>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

// GET /auth/me
export async function getMe(token: string): Promise<UserOut> {
  const { data } = await authAxios.get<UserOut>('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

// Admin: GET /auth/users
export async function listUsers(token: string): Promise<UserOut[]> {
  const { data } = await authAxios.get<UserOut[]>('/auth/users', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

// Admin: POST /auth/users
export async function createUser(token: string, req: CreateUserRequest): Promise<UserOut> {
  const { data } = await authAxios.post<UserOut>('/auth/users', req, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

// Admin: PATCH /auth/users/{id}
export async function updateUser(token: string, id: string, req: UpdateUserRequest): Promise<UserOut> {
  const { data } = await authAxios.patch<UserOut>(`/auth/users/${id}`, req, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

// Admin: DELETE /auth/users/{id}
export async function deactivateUser(token: string, id: string): Promise<void> {
  await authAxios.delete(`/auth/users/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}
