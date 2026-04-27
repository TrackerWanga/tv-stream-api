export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace('/v1', '');
    
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300'
    };

    try {
      // GET /channels/:id/live
      const liveMatch = path.match(/^\/channels\/(.+)\/live$/);
      if (liveMatch) {
        const channelId = liveMatch[1];
        const streams = await env.TV_KV.get(`streams:${channelId}`, 'json');
        
        if (!streams || streams.length === 0) {
          return Response.json({ 
            error: 'No stream available',
            channelId 
          }, { status: 404, headers });
        }

        // Sort by quality preference
        const qualityOrder = { '4K': 4, '1080p': 3, '720p': 2, 'SD': 1 };
        const sorted = streams.sort((a, b) => 
          (qualityOrder[b.quality] || 0) - (qualityOrder[a.quality] || 0)
        );
        
        return Response.json({
          channelId,
          primary: sorted[0],
          alternatives: sorted.slice(1, 4)
        }, { headers });
      }

      return Response.json({ error: 'Not found' }, { status: 404, headers });

    } catch (e) {
      return Response.json({ error: e.message }, { status: 500, headers });
    }
  }
};
