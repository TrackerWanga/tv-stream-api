export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    const headers = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Content-Type': 'application/json'
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }

    // Health check
    if (path === '/health') {
      return Response.json({
        status: 'ok',
        version: '1.0.0',
        workers: ['gateway', 'channels', 'streams', 'schedule'],
        docs: 'https://github.com/TrackerWanga/tv-stream-api'
      }, { headers });
    }

    // API root - documentation
    if (path === '/' || path === '/v1' || path === '/v1/') {
      return Response.json({
        name: 'TV Stream API',
        version: '1.0.0',
        endpoints: {
          channels: '/v1/channels',
          search: '/v1/channels/search?q={name}',
          channelById: '/v1/channels/:id',
          live: '/v1/channels/:id/live',
          schedule: '/v1/channels/:id/schedule',
          whatsOnNow: '/v1/schedule?time=now',
          categories: '/v1/categories',
          countries: '/v1/countries',
          health: '/health'
        }
      }, { headers });
    }

    // Route to sub-workers
    try {
      if (path.startsWith('/v1/channels') && path.includes('/live')) {
        return env.STREAMS.fetch(request);
      }
      if (path.startsWith('/v1/channels') && path.includes('/schedule')) {
        return env.SCHEDULE.fetch(request);
      }
      if (path.startsWith('/v1/schedule')) {
        return env.SCHEDULE.fetch(request);
      }
      if (path.startsWith('/v1/channels') || path.startsWith('/v1/categories') || path.startsWith('/v1/countries')) {
        return env.CHANNELS.fetch(request);
      }

      return Response.json({ 
        error: 'Not found',
        docs: '/'
      }, { status: 404, headers });

    } catch (e) {
      return Response.json({ error: e.message }, { status: 500, headers });
    }
  }
};
