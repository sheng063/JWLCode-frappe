import { fileURLToPath } from 'node:url';
export const colyseusSandboxStorage = {
  name: 'colyseus-sandbox-storage',
  setup(build) {
    build.onResolve({ filter: /^\.\/Storage\.mjs$/ }, args => {
      if (args.importer.replaceAll('\\', '/').includes('/@colyseus/sdk/build/')) {
        return { path: fileURLToPath(new URL('./storage.js', import.meta.url)) };
      }
    });
  },
};
