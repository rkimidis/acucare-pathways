/**
 * Copy Dictionary System
 *
 * Provides versioned, reviewable copy for the patient portal.
 * All user-facing text should come from this system.
 */

export { copy } from './en-GB';
export type { CopyDictionary } from './en-GB';

/**
 * Render a template string with parameters.
 *
 * @example
 * renderTemplate("Step {{current}} of {{total}}", { current: 1, total: 5 })
 * // => "Step 1 of 5"
 */
export function renderTemplate(
  template: string,
  params: Record<string, string | number>
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => String(params[key] ?? ''));
}

/**
 * Type-safe copy accessor with optional template rendering.
 *
 * @example
 * getCopy('patient.intake.progress.stepLabel', { current: 1, total: 5, label: 'About you' })
 */
export function getCopy(
  path: string,
  params?: Record<string, string | number>
): string {
  const { copy } = require('./en-GB');
  const keys = path.split('.');
  let value: unknown = copy;

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = (value as Record<string, unknown>)[key];
    } else {
      console.warn(`Copy key not found: ${path}`);
      return path;
    }
  }

  if (typeof value !== 'string') {
    console.warn(`Copy key is not a string: ${path}`);
    return path;
  }

  return params ? renderTemplate(value, params) : value;
}

/**
 * Hook for accessing copy in React components.
 * Returns the copy object and helper functions.
 */
export function useCopy() {
  const { copy } = require('./en-GB');

  return {
    copy,
    render: renderTemplate,
    get: getCopy,
  };
}
