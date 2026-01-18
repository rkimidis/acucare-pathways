'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { setToken } from '@/lib/auth';
import styles from '../auth.module.css';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode] = useState('');
  const [userId, setUserId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/v1/auth/staff/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Login failed');
      }

      const data = await response.json();

      // Check if MFA is required
      if (data.mfa_required) {
        setMfaRequired(true);
        setUserId(data.user_id);
      } else {
        setToken(data.access_token);
        router.push('/dashboard');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/v1/auth/staff/mfa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, otp_code: mfaCode }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'MFA verification failed');
      }

      // MFA verified - get new token with full access
      // In production, this would return a new JWT
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'MFA verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <div className={styles.logo}>AcuCare Pathways</div>
        <h1 className={styles.title}>Staff Sign In</h1>

        {!mfaRequired ? (
          <form onSubmit={handleLogin} className={styles.form}>
            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.field}>
              <label htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@acucare.local"
                required
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength={8}
              />
            </div>

            <button
              type="submit"
              className={styles.submitButton}
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaVerify} className={styles.form}>
            <div className={styles.mfaInfo}>
              <p>Enter the 6-digit code from your authenticator app.</p>
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.field}>
              <label htmlFor="mfaCode">Authentication Code</label>
              <input
                type="text"
                id="mfaCode"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                placeholder="000000"
                required
                maxLength={6}
                pattern="[0-9]{6}"
                className={styles.mfaInput}
              />
            </div>

            <button
              type="submit"
              className={styles.submitButton}
              disabled={loading}
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>

            <button
              type="button"
              className={styles.backButton}
              onClick={() => setMfaRequired(false)}
            >
              Back to login
            </button>
          </form>
        )}

        <div className={styles.links}>
          <Link href="/">Back to home</Link>
        </div>
      </div>
    </main>
  );
}
