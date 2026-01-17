'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { removeToken } from '@/lib/auth';
import { AppShell, EmptyState, PageHeader } from '@/ui/components';
import styles from './reporting.module.css';

interface TierVolume {
  tier: string;
  count: number;
  percentage: number;
}

interface PathwayVolume {
  pathway: string;
  count: number;
  percentage: number;
}

interface WaitTimeMetrics {
  tier: string;
  avg_days: number;
  median_days: number;
  sla_target_days: number;
  breaches: number;
  breach_percentage: number;
}

interface NoShowMetrics {
  total_appointments: number;
  no_shows: number;
  no_show_rate: number;
}

interface OutcomeTrend {
  period: string;
  completed: number;
  discharged: number;
  escalated: number;
  declined: number;
}

interface AlertSummary {
  total_alerts: number;
  total_resolved: number;
  by_severity: Record<string, { total: number; resolved: number }>;
}

const TIER_COLORS: Record<string, string> = {
  red: '#dc2626',
  amber: '#f59e0b',
  green: '#16a34a',
  blue: '#3b82f6',
};

export default function ReportingPage() {
  const router = useRouter();
  const [tierVolumes, setTierVolumes] = useState<TierVolume[]>([]);
  const [pathwayVolumes, setPathwayVolumes] = useState<PathwayVolume[]>([]);
  const [waitTimes, setWaitTimes] = useState<WaitTimeMetrics[]>([]);
  const [noShows, setNoShows] = useState<NoShowMetrics | null>(null);
  const [outcomeTrends, setOutcomeTrends] = useState<OutcomeTrend[]>([]);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dateRange, setDateRange] = useState({
    start: '',
    end: '',
  });

  useEffect(() => {
    loadDashboardData();
  }, [dateRange]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);

      const response = await fetch(`/api/v1/reporting/dashboard?${params}`);
      if (!response.ok) throw new Error('Failed to load dashboard data');

      const data = await response.json();
      setTierVolumes(data.tier_volumes || []);
      setPathwayVolumes(data.pathway_volumes || []);
      setWaitTimes(data.wait_times || []);
      setNoShows(data.no_shows || null);
      setOutcomeTrends(data.outcome_trends || []);
      setAlertSummary(data.alert_summary || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getTotalCases = () => {
    return tierVolumes.reduce((sum, v) => sum + v.count, 0);
  };

  const getTotalBreaches = () => {
    return waitTimes.reduce((sum, w) => sum + w.breaches, 0);
  };

  const handleLogout = () => {
    removeToken();
    router.push('/');
  };

  return (
    <AppShell activeNav="reporting" onSignOut={handleLogout}>
      <PageHeader
        title="Reports & Analytics"
        breadcrumb={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Reporting' },
        ]}
        actions={
          <div className={styles.dateFilters}>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className={styles.dateInput}
            />
            <span>to</span>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className={styles.dateInput}
            />
          </div>
        }
      />

      {loading ? (
        <EmptyState title="Loading dashboard data" variant="loading" />
      ) : (
        <div className={styles.content}>
          {error && <div className={styles.error}>{error}</div>}
            {/* Summary Cards */}
            <div className={styles.summaryCards}>
              <div className={styles.summaryCard}>
                <span className={styles.summaryValue}>{getTotalCases()}</span>
                <span className={styles.summaryLabel}>Total Cases</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryValue}>{noShows?.no_show_rate.toFixed(1) || 0}%</span>
                <span className={styles.summaryLabel}>No-Show Rate</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryValue}>{getTotalBreaches()}</span>
                <span className={styles.summaryLabel}>SLA Breaches</span>
              </div>
              <div className={styles.summaryCard}>
                <span className={styles.summaryValue}>{alertSummary?.total_alerts || 0}</span>
                <span className={styles.summaryLabel}>Total Alerts</span>
              </div>
            </div>

            <div className={styles.chartsRow}>
              {/* Volumes by Tier */}
              <div className={styles.chartCard}>
                <h2>Cases by Tier</h2>
                <div className={styles.tierBars}>
                  {tierVolumes.map((volume) => (
                    <div key={volume.tier} className={styles.tierBar}>
                      <div className={styles.tierBarLabel}>
                        <span
                          className={styles.tierDot}
                          style={{ backgroundColor: TIER_COLORS[volume.tier] || '#64748b' }}
                        />
                        <span>{volume.tier.toUpperCase()}</span>
                      </div>
                      <div className={styles.tierBarTrack}>
                        <div
                          className={styles.tierBarFill}
                          style={{
                            width: `${volume.percentage}%`,
                            backgroundColor: TIER_COLORS[volume.tier] || '#64748b',
                          }}
                        />
                      </div>
                      <span className={styles.tierBarValue}>
                        {volume.count} ({volume.percentage.toFixed(1)}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Volumes by Pathway */}
              <div className={styles.chartCard}>
                <h2>Cases by Pathway</h2>
                <div className={styles.pathwayList}>
                  {pathwayVolumes.map((volume, index) => (
                    <div key={volume.pathway} className={styles.pathwayItem}>
                      <span className={styles.pathwayName}>{volume.pathway}</span>
                      <div className={styles.pathwayBarTrack}>
                        <div
                          className={styles.pathwayBarFill}
                          style={{ width: `${volume.percentage}%` }}
                        />
                      </div>
                      <span className={styles.pathwayValue}>{volume.count}</span>
                    </div>
                  ))}
                  {pathwayVolumes.length === 0 && (
                    <p className={styles.noData}>No pathway data available</p>
                  )}
                </div>
              </div>
            </div>

            {/* Wait Times & SLA */}
            <div className={styles.chartCard}>
              <h2>Wait Times & SLA Compliance</h2>
              <div className={styles.slaTable}>
                <table>
                  <thead>
                    <tr>
                      <th>Tier</th>
                      <th>SLA Target</th>
                      <th>Avg Wait</th>
                      <th>Median Wait</th>
                      <th>Breaches</th>
                      <th>Breach Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {waitTimes.map((metric) => (
                      <tr key={metric.tier}>
                        <td>
                          <span
                            className={styles.tierBadge}
                            style={{ backgroundColor: TIER_COLORS[metric.tier] || '#64748b' }}
                          >
                            {metric.tier.toUpperCase()}
                          </span>
                        </td>
                        <td>{metric.sla_target_days} days</td>
                        <td>{metric.avg_days.toFixed(1)} days</td>
                        <td>{metric.median_days.toFixed(1)} days</td>
                        <td>{metric.breaches}</td>
                        <td>
                          <span className={metric.breach_percentage > 10 ? styles.breachHigh : styles.breachLow}>
                            {metric.breach_percentage.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={styles.chartsRow}>
              {/* No-Shows */}
              <div className={styles.chartCard}>
                <h2>No-Show Statistics</h2>
                {noShows ? (
                  <div className={styles.noShowStats}>
                    <div className={styles.noShowMain}>
                      <div className={styles.noShowCircle}>
                        <span className={styles.noShowRate}>
                          {noShows.no_show_rate.toFixed(1)}%
                        </span>
                        <span className={styles.noShowLabel}>No-Show Rate</span>
                      </div>
                    </div>
                    <div className={styles.noShowDetails}>
                      <div className={styles.noShowDetail}>
                        <span className={styles.noShowDetailLabel}>Total Appointments</span>
                        <span className={styles.noShowDetailValue}>{noShows.total_appointments}</span>
                      </div>
                      <div className={styles.noShowDetail}>
                        <span className={styles.noShowDetailLabel}>No-Shows</span>
                        <span className={styles.noShowDetailValue}>{noShows.no_shows}</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className={styles.noData}>No appointment data available</p>
                )}
              </div>

              {/* Alert Summary */}
              <div className={styles.chartCard}>
                <h2>Monitoring Alerts</h2>
                {alertSummary ? (
                  <div className={styles.alertStats}>
                    <div className={styles.alertOverview}>
                      <div className={styles.alertStat}>
                        <span className={styles.alertStatValue}>{alertSummary.total_alerts}</span>
                        <span className={styles.alertStatLabel}>Total</span>
                      </div>
                      <div className={styles.alertStat}>
                        <span className={styles.alertStatValue}>{alertSummary.total_resolved}</span>
                        <span className={styles.alertStatLabel}>Resolved</span>
                      </div>
                      <div className={styles.alertStat}>
                        <span className={styles.alertStatValue}>
                          {alertSummary.total_alerts - alertSummary.total_resolved}
                        </span>
                        <span className={styles.alertStatLabel}>Open</span>
                      </div>
                    </div>
                    <div className={styles.alertBySeverity}>
                      {Object.entries(alertSummary.by_severity).map(([severity, data]) => (
                        <div key={severity} className={styles.severityRow}>
                          <span className={styles.severityLabel}>{severity}</span>
                          <span className={styles.severityValue}>
                            {data.total} ({data.resolved} resolved)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className={styles.noData}>No alert data available</p>
                )}
              </div>
            </div>

            {/* Outcome Trends */}
            <div className={styles.chartCard}>
              <h2>Outcome Trends</h2>
              {outcomeTrends.length > 0 ? (
                <div className={styles.trendsTable}>
                  <table>
                    <thead>
                      <tr>
                        <th>Period</th>
                        <th>Completed</th>
                        <th>Discharged</th>
                        <th>Escalated</th>
                        <th>Declined</th>
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outcomeTrends.map((trend) => (
                        <tr key={trend.period}>
                          <td>{trend.period}</td>
                          <td className={styles.trendCompleted}>{trend.completed}</td>
                          <td className={styles.trendDischarged}>{trend.discharged}</td>
                          <td className={styles.trendEscalated}>{trend.escalated}</td>
                          <td className={styles.trendDeclined}>{trend.declined}</td>
                          <td className={styles.trendTotal}>
                            {trend.completed + trend.discharged + trend.escalated + trend.declined}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className={styles.noData}>No outcome data available</p>
              )}
            </div>
        </div>
      )}
    </AppShell>
  );
}
