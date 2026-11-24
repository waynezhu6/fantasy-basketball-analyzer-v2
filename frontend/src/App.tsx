import { useEffect, useState } from 'react'
import { api, loginUrl } from './api'

type User = { id: string; name: string }

function App() {
  const [health, setHealth] = useState('checking…')
  const [user, setUser] = useState<User | null | undefined>(undefined)

  useEffect(() => {
    api('/health')
      .then((res) => res.json())
      .then((body: { status: string }) => setHealth(body.status))
      .catch(() => setHealth('unreachable'))
    api('/me')
      .then((res) => (res.ok ? (res.json() as Promise<User>) : null))
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  return (
    <div>
      <h1>Hello World</h1>
      <p>Backend: {health}</p>
      {user === undefined ? null : user ? (
        <p>Signed in as {user.name}</p>
      ) : (
        <p>
          <a href={loginUrl()}>Sign in</a>
        </p>
      )}
    </div>
  )
}

export default App
