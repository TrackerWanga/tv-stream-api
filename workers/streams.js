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
      const liveMatch = path.match(/^\/channels\/(.+)\/live$/);
      if (!liveMatch) {
        return Response.json({ error: 'Not found' }, { status: 404, headers });
      }

      const channelId = decodeURIComponent(liveMatch[1]);
      
      // Strategy 1: Exact match
      let streams = await env.TV_KV.get('streams:' + channelId, 'json');
      
      // Strategy 2: Lowercase
      if (!streams) {
        streams = await env.TV_KV.get('streams:' + channelId.toLowerCase(), 'json');
      }
      
      // Strategy 3: Replace dots with dashes
      if (!streams) {
        const dashed = channelId.toLowerCase().replace(/\./g, '-');
        streams = await env.TV_KV.get('streams:' + dashed, 'json');
      }
      
      // Strategy 4: Search KV by first part of name
      if (!streams) {
        const firstWord = channelId.toLowerCase().split(/[.-]/)[0];
        const keyList = await env.TV_KV.list({ prefix: 'streams:' + firstWord, limit: 20 });
        
        for (const k of keyList.keys) {
          const candidate = await env.TV_KV.get(k.name, 'json');
          if (candidate && candidate.length > 0) {
            streams = candidate;
            break;
          }
        }
      }
      
      if (!streams || streams.length === 0) {
        return Response.json({ 
          error: 'No stream available',
          channelId: channelId
        }, { status: 404, headers });
      }

      // Sort by quality
      const qualityOrder = { '4K': 4, '1080p': 3, '720p': 2, 'SD': 1 };
      const sorted = streams.sort(function(a, b) {
        return (qualityOrder[b.quality] || 0) - (qualityOrder[a.quality] || 0);
      });
      
      return Response.json({
        channelId: channelId,
        primary: sorted[0],
        alternatives: sorted.slice(1, 4)
      }, { headers });

    } catch (e) {
      return Response.json({ error: e.message }, { status: 500, headers });
    }
  }
};
