import type { Handle } from '@sveltejs/kit';

// Docker環境では内部ネットワークを使用
const API_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

// SvelteKitのデフォルトのbody size limitを回避するため、
// file uploadは直接fetchを使用
export const handle: Handle = async ({ event, resolve }) => {
    // APIリクエストをプロキシ
    if (event.url.pathname.startsWith('/api')) {
        const apiUrl = `${API_URL}${event.url.pathname}`;
        
        console.log(`Proxying request to: ${apiUrl}`);
        
        try {
            // multipart/form-dataの場合は特別な処理
            const contentType = event.request.headers.get('content-type') || '';
            
            let body;
            if (contentType.includes('multipart/form-data')) {
                // multipart/form-dataの場合はそのまま転送
                body = event.request.body;
            } else {
                // その他の場合は通常通り
                body = await event.request.arrayBuffer();
            }
            
            // リクエストヘッダーをコピー（Host以外）
            const headers = new Headers();
            event.request.headers.forEach((value, key) => {
                if (key.toLowerCase() !== 'host' && key.toLowerCase() !== 'connection') {
                    headers.set(key, value);
                }
            });
            
            const response = await fetch(apiUrl, {
                method: event.request.method,
                headers: headers,
                body: event.request.method !== 'GET' && event.request.method !== 'HEAD' ? body : undefined,
                // @ts-ignore
                duplex: 'half' // streaming bodyのために必要
            });

            // レスポンスヘッダーをコピー
            const responseHeaders = new Headers();
            response.headers.forEach((value, key) => {
                responseHeaders.set(key, value);
            });

            return new Response(response.body, {
                status: response.status,
                statusText: response.statusText,
                headers: responseHeaders
            });
        } catch (error) {
            console.error('Proxy error:', error);
            console.error('Failed URL:', apiUrl);
            return new Response(`Proxy Error: ${error}`, { status: 502 });
        }
    }

    // body size limitを増やす
    return await resolve(event, {
        transformPageChunk: ({ html }) => html
    });
};