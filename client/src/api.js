const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

let token = '';

export const setToken = t => {
    token = t;
};

export async function api(path, options = {}) {
    const r = await fetch(base + '/api' + path, {
        ...options,
        headers: {
            Authorization: 'Bearer ' + token,
            ...(!(options.body instanceof FormData)
                ? { 'Content-Type': 'application/json' }
                : {}),
            ...options.headers
        }
    });

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
}

export const action = (op, args = {}) =>
    api('/actions/' + op, {
        method: 'POST',
        body: JSON.stringify(args)
    });

export async function download(id, ext) {
    const r = await fetch(
        base + '/api/reports/' + id + '/download/' + ext,
        {
            headers: {
                Authorization: 'Bearer ' + token
            }
        }
    );

    if (!r.ok) throw new Error('Download failed');

    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement('a');

    a.href = url;
    a.download = 'ESS-report.' + ext;
    a.click();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
}