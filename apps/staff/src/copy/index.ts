/**
 * Staff Console Copy Exports
 */

export { copy } from './en-GB';
export type { StaffCopyDictionary } from './en-GB';

/**
 * Template rendering helper.
 * Replaces {{variable}} placeholders with values from params.
 */
export function renderTemplate(
  template: string,
  params: Record<string, string | number>
): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) =>
    String(params[key] ?? '')
  );
}
