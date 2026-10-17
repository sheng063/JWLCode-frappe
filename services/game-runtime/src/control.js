export class ControlPlane {
  constructor({ url, site, deployment, serviceKey }) {
    Object.assign(this, { url, site, deployment, serviceKey });
  }
  async call(method, body = {}) {
    const response = await fetch(`${this.url}/api/method/lms.lms.game_runtime.${method}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json',
        'X-Frappe-Site-Name': this.site, 'X-Game-Deployment': this.deployment,
        'X-Game-Service-Key': this.serviceKey },
      body: JSON.stringify(body), signal: AbortSignal.timeout(4000),
    });
    if (!response.ok) throw new Error('Game authorization unavailable');
    const result = await response.json();
    if (!result.message) throw new Error('Invalid control response');
    return result.message;
  }
}
