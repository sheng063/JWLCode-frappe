// Keep the page's scheme. A site served on HTTP port 80 has no location.port;
// inferring HTTPS from an empty port silently disables realtime notifications.
export function socketUrl(location, socketPort, siteName) {
 const port = location.port ? `:${socketPort}` : ''
 return `${location.protocol}//${location.hostname}${port}/${siteName}`
}
