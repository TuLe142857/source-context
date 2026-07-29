/**
 * Shared helper for the `*.template.ts` modules — functions here back UI
 * flows the product needs but the backend doesn't expose yet (see
 * "Missing-API Items" in plans/frontend_dev_plan.md). They deliberately do
 * NOT simulate success with mock data (hard to keep consistent / misleading
 * during a demo) — they reject with a distinct, catchable error so the UI
 * can surface a clear "not available yet" message instead of pretending the
 * action succeeded.
 */
export class TemplateNotImplementedError extends Error {
  constructor(featureName: string) {
    super(`"${featureName}" chưa được backend hỗ trợ (UI template, chưa có API thật).`);
    this.name = 'TemplateNotImplementedError';
  }
}

export function notImplemented<T = never>(featureName: string): Promise<T> {
  return Promise.reject(new TemplateNotImplementedError(featureName));
}
