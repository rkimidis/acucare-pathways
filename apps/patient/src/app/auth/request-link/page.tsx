'use client';

import { useState } from 'react';
import Link from 'next/link';
import styles from '../auth.module.css';

export default function RequestLinkPage() {
  const [email, setEmail] = useState('');
  const [success, setSuccess] = useState(false);
  const [devToken, setDevToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    setLoading(true);

    try {
      const response = await fetch('/api/v1/auth/patient/request-magic-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Request failed');
      }

      const data = await response.json();
      setSuccess(true);
      // In dev mode, the token is returned directly
      if (data.token) {
        setDevToken(data.token);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1 className={styles.title}>Request Magic Link</h1>
        <p className={styles.description}>
          Enter your email address and we will send you a sign-in link.
        </p>

        {success ? (
          <div className={styles.successBox}>
            <h2>Check your email</h2>
            <p>
              If an account exists for {email}, you will receive a magic link
              shortly.
            </p>
            {devToken && (
              <div className={styles.devToken}>
                <p>
                  <strong>Development Mode:</strong> Use this token to sign in:
                </p>
                <code>{devToken}</code>
              </div>
            )}
            <Link href="/auth/login" className={styles.submitButton}>
              Go to Sign In
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.form}>
            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.field}>
              <label htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>

            <button
              type="submit"
              className={styles.submitButton}
              disabled={loading}
            >
              {loading ? 'Sending...' : 'Send Magic Link'}
            </button>
          </form>
        )}

        <div className={styles.links}>
          <Link href="/auth/login">Already have a token? Sign in</Link>
          <Link href="/">Back to home</Link>
        </div>
      </div>
    </main>
  );
}
