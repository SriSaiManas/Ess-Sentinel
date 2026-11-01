const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

// Retained for backward compatibility
export const setToken = () => {};

// Sleep helper for exponential backoff during cold starts
const wait = ms => new Promise(res => setTimeout(res, ms));

const defaultRetries = (typeof globalThis !== 'undefined' && globalThis.__ESS_TEST__) ? 0 : 2;

export async function api(path, options = {}, retries = defaultRetries) {
    const url = base + '/api' + path;
    const fetchOptions = {
        ...options,
        headers: {
            ...(!(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
            ...options.headers
        }
    };

    let lastError = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s request timeout

            const r = await fetch(url, {
                ...fetchOptions,
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            // Cold start detection: 502/503/504 on initial request
            if ((r.status === 502 || r.status === 503 || r.status === 504) && attempt < retries) {
                await wait(1000 * Math.pow(2, attempt)); // 1s, 2s
                continue;
            }

            if (!r.ok) {
                let d;
                try {
                    d = await r.json();
                } catch {}

                throw new Error(
                    d?.error?.message || 'Service unavailable (' + r.status + ')'
                );
            }

            return r.status === 204 ? null : r.json();
        } catch (err) {
            lastError = err;
            if (err.name === 'AbortError') {
                throw new Error('Request timed out. The backend service may still be warming up.');
            }
            // Retry transient network errors
            if (attempt < retries && (err.message.includes('fetch') || err.message.includes('network') || err.message.includes('Failed'))) {
                await wait(1000 * Math.pow(2, attempt));
                continue;
            }
            throw err;
        }
    }

    throw lastError || new Error('Request failed');
}

export const action = (op, args = {}) =>
    api('/actions/' + op, {
        method: 'POST',
        body: JSON.stringify(args)
    });

export async function download(id, ext) {
    const r = await fetch(base + '/api/reports/' + id + '/download/' + ext);

    if (!r.ok) {
        let msg = 'Download failed';
        try {
            const d = await r.json();
            if (d?.error?.message) msg = d.error.message;
        } catch {}
        throw new Error(msg);
    }

    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');

    a.href = url;
    a.download = 'ESS-report.' + ext;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    setTimeout(() => URL.revokeObjectURL(url), 1000);
}