'use client';

import { ReactNode } from 'react';
import Link from 'next/link';

// AppShell - Main layout wrapper with navigation
interface AppShellProps {
  children: ReactNode;
  activeNav?: string;
  onSignOut?: () => void;
}

export function AppShell({ children, activeNav, onSignOut }: AppShellProps) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', href: '/dashboard' },
    { id: 'triage', label: 'Triage', href: '/dashboard/triage' },
    { id: 'patients', label: 'Patients', href: '/dashboard/patients' },
    { id: 'scheduling', label: 'Scheduling', href: '/dashboard/scheduling' },
    { id: 'referrals', label: 'Referrals', href: '/dashboard/referrals' },
    { id: 'monitoring', label: 'Monitoring', href: '/dashboard/monitoring' },
    { id: 'audit', label: 'Audit', href: '/dashboard/audit' },
    { id: 'incidents', label: 'Incidents', href: '/dashboard/incidents' },
    { id: 'change-control', label: 'Change Control', href: '/dashboard/change-control' },
    { id: 'reporting', label: 'Reporting', href: '/dashboard/reporting' },
    { id: 'pilot', label: 'Pilot Feedback', href: '/governance/pilot-feedback' },
  ];

  return (
    <div className="appShell">
      <header className="appShellHeader">
        <div className="appShellBrand">AcuCare Pathways</div>
        {onSignOut && (
          <button className="appShellSignOut" onClick={onSignOut}>
            Sign Out
          </button>
        )}
      </header>
      <div className="appShellBody">
        <aside className="appShellSidebar">
          <nav className="appShellNav" aria-label="Primary">
            {navItems.map((item) => {
              const isActive = activeNav === item.id;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={isActive ? 'appShellNavItem appShellNavItemActive' : 'appShellNavItem'}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <main className="appShellMain">{children}</main>
      </div>
    </div>
  );
}

// PageHeader - Page title and metadata
interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  metaText?: string;
  statusPill?: ReactNode;
  className?: string;
  breadcrumb?: BreadcrumbItem[];
  actions?: ReactNode;
}

export function PageHeader({ title, metaText, statusPill, className, breadcrumb, actions }: PageHeaderProps) {
  return (
    <div className={className} style={{ marginBottom: '1.5rem' }}>
      {breadcrumb && breadcrumb.length > 0 && (
        <nav style={{ marginBottom: '0.5rem', fontSize: '0.875rem' }}>
          {breadcrumb.map((item, idx) => (
            <span key={idx}>
              {idx > 0 && <span style={{ margin: '0 0.5rem', color: '#9ca3af' }}>/</span>}
              {item.href ? (
                <Link href={item.href} style={{ color: '#6b7280', textDecoration: 'none' }}>
                  {item.label}
                </Link>
              ) : (
                <span style={{ color: '#374151' }}>{item.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{title}</h1>
          {statusPill}
        </div>
        {actions}
      </div>
      {metaText && (
        <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>{metaText}</p>
      )}
    </div>
  );
}

// StatusBadge - Status indicator pill
interface StatusBadgeProps {
  tone: 'green' | 'amber' | 'red' | 'blue' | 'grey' | 'neutral';
  label: string;
}

export function StatusBadge({ tone, label }: StatusBadgeProps) {
  const colors = {
    green: { bg: '#dcfce7', text: '#166534' },
    amber: { bg: '#fef3c7', text: '#92400e' },
    red: { bg: '#fee2e2', text: '#991b1b' },
    blue: { bg: '#dbeafe', text: '#1e40af' },
    grey: { bg: '#f3f4f6', text: '#374151' },
    neutral: { bg: '#f3f4f6', text: '#374151' },
  };
  const color = colors[tone] || colors.grey;

  return (
    <span
      style={{
        background: color.bg,
        color: color.text,
        padding: '0.25rem 0.75rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 500,
      }}
    >
      {label}
    </span>
  );
}

// StatCard - KPI card with value
interface StatCardProps {
  label: string;
  value: string | number;
  href?: string;
  footer?: ReactNode;
  subtitle?: ReactNode;
  tone?: 'default' | 'red' | 'amber' | 'green' | 'blue';
  active?: boolean;
  onClick?: () => void;
}

export function StatCard({ label, value, href, footer, subtitle, tone = 'default', active, onClick }: StatCardProps) {
  const toneColors = {
    default: '#1e40af',
    red: '#dc2626',
    amber: '#d97706',
    green: '#059669',
    blue: '#2563eb',
  };

  const content = (
    <div
      style={{
        background: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '0.5rem',
        padding: '1rem',
        minWidth: '120px',
      }}
    >
      <p style={{ color: '#6b7280', fontSize: '0.75rem', margin: 0 }}>{label}</p>
      <p
        style={{
          fontSize: '1.5rem',
          fontWeight: 'bold',
          color: toneColors[tone],
          margin: '0.25rem 0',
        }}
      >
        {value}
      </p>
      {subtitle && <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{subtitle}</div>}
      {footer}
    </div>
  );

  if (href) {
    return (
      <Link href={href} style={{ textDecoration: 'none' }}>
        {content}
      </Link>
    );
  }

  return content;
}

// EmptyState - Placeholder for empty data
interface EmptyStateProps {
  title: string;
  description?: string;
  message?: string;
  action?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  variant?: 'default' | 'loading' | 'error';
}

export function EmptyState({ title, description, message, action, actionLabel, onAction, variant = 'default' }: EmptyStateProps) {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '3rem',
        background: variant === 'error' ? '#fef2f2' : '#f9fafb',
        borderRadius: '0.5rem',
      }}
    >
      {variant === 'loading' && (
        <div style={{ marginBottom: '1rem', color: '#6b7280' }}>Loading...</div>
      )}
      <h3 style={{
        fontSize: '1.125rem',
        fontWeight: 600,
        marginBottom: '0.5rem',
        color: variant === 'error' ? '#991b1b' : 'inherit'
      }}>{title}</h3>
      {(description || message) && (
        <p style={{ color: '#6b7280', marginBottom: '1rem' }}>{description || message}</p>
      )}
      {action}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            background: '#1e40af',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

// Button - Standard button component
interface ButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'tertiary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit';
  className?: string;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  disabled,
  type = 'button',
}: ButtonProps) {
  const variants = {
    primary: { bg: '#1e40af', color: 'white', border: 'none' },
    secondary: { bg: '#e5e7eb', color: '#374151', border: 'none' },
    danger: { bg: '#dc2626', color: 'white', border: 'none' },
    tertiary: { bg: 'transparent', color: '#1e40af', border: 'none' },
    ghost: { bg: 'transparent', color: '#374151', border: '1px solid #e5e7eb' },
  };
  const sizes = {
    sm: { padding: '0.375rem 0.75rem', fontSize: '0.875rem' },
    md: { padding: '0.5rem 1rem', fontSize: '1rem' },
    lg: { padding: '0.75rem 1.5rem', fontSize: '1.125rem' },
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{
        ...variants[variant],
        ...sizes[size],
        border: 'none',
        borderRadius: '0.375rem',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {children}
    </button>
  );
}

// SegmentedControl - Tab-like selector
interface SegmentedControlProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}

export function SegmentedControl({ options, value, onChange }: SegmentedControlProps) {
  return (
    <div
      style={{
        display: 'inline-flex',
        background: '#f3f4f6',
        borderRadius: '0.375rem',
        padding: '0.25rem',
      }}
    >
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          style={{
            padding: '0.5rem 1rem',
            border: 'none',
            borderRadius: '0.25rem',
            background: value === option.value ? 'white' : 'transparent',
            color: value === option.value ? '#1e40af' : '#6b7280',
            fontWeight: value === option.value ? 600 : 400,
            cursor: 'pointer',
            boxShadow: value === option.value ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
