const MAX_DELETIONS_PER_RUN = 2_000;

async function defaultCleanup(event, now = new Date()) {
  const blobs = await import('@netlify/blobs');
  if (typeof blobs.connectLambda === 'function') blobs.connectLambda(event);
  const store = blobs.getStore({ name: 'ltg-analytics-events' });
  const cutoff = new Date(now.getTime() - (180 * 24 * 60 * 60 * 1000)).toISOString().slice(0, 10);
  let deleted = 0;
  let scanned = 0;

  for await (const page of store.list({ paginate: true })) {
    for (const blob of page.blobs || []) {
      scanned += 1;
      const day = String(blob.key || '').slice(0, 10);
      if (/^\d{4}-\d{2}-\d{2}$/.test(day) && day < cutoff) {
        await store.delete(blob.key);
        deleted += 1;
        if (deleted >= MAX_DELETIONS_PER_RUN) {
          return { deleted, scanned, cutoff, limited: true };
        }
      }
    }
  }
  return { deleted, scanned, cutoff, limited: false };
}

function createHandler(overrides = {}) {
  const cleanup = overrides.cleanup || defaultCleanup;
  const nowFactory = overrides.now || (() => new Date());
  return async function handler(event) {
    let scheduled = Boolean(event && (event.next_run || event.blobs_retention_job));
    if (!scheduled && event && event.body) {
      try {
        const payload = JSON.parse(event.body);
        scheduled = Boolean(payload && payload.next_run);
      } catch {
        scheduled = false;
      }
    }
    if (!scheduled) {
      return { statusCode: 404, body: 'Not found' };
    }
    try {
      const result = await cleanup(event, nowFactory());
      return { statusCode: 200, body: JSON.stringify({ ok: true, ...result }) };
    } catch (error) {
      console.error('analytics retention error:', error.message);
      return { statusCode: 500, body: JSON.stringify({ error: 'Retention cleanup failed' }) };
    }
  };
}

exports.createHandler = createHandler;
exports.handler = createHandler();
