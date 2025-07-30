import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			out: 'build',
			// Node.jsのボディサイズ制限を増やす
			env: {
				BODY_SIZE_LIMIT: '52428800' // 50MB
			}
		}),
		// SvelteKitのボディサイズ制限を増やす
		csrf: {
			checkOrigin: false
		}
	}
};

export default config;