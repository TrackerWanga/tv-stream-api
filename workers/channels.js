export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace('/v1', '');
    const params = url.searchParams;
    
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=3600'
    };

    try {
      // GET /channels/search?q=BBC
      if (path === '/channels/search') {
        const q = (params.get('q') || '').toLowerCase();
        if (!q || q.length < 1) {
          return Response.json({ error: 'Query parameter ?q= required' }, { status: 400, headers });
        }
        
        // Search in lightweight index
        const light = await env.TV_KV.get('channels:light', 'json');
        const results = light.filter(c => 
          c.name.toLowerCase().includes(q) ||
          c.id.toLowerCase().includes(q)
        ).slice(0, 50);
        
        return Response.json({
          query: q,
          count: results.length,
          results
        }, { headers });
      }

      // GET /channels/:id
      const idMatch = path.match(/^\/channels\/([^\/]+)$/);
      if (idMatch) {
        const channelId = idMatch[1];
        const channel = await findChannel(env, channelId);
        
        if (!channel) {
          return Response.json({ error: 'Channel not found' }, { status: 404, headers });
        }
        
        return Response.json({
          ...channel,
          _links: {
            live: `/v1/channels/${channel.id}/live`,
            schedule: `/v1/channels/${channel.id}/schedule`
          }
        }, { headers });
      }

      // GET /channels (with optional filters)
      if (path === '/channels' || path === '') {
        const country = params.get('country');
        const category = params.get('category');
        const language = params.get('language');
        const page = parseInt(params.get('page') || '1');
        const limit = Math.min(parseInt(params.get('limit') || '50'), 200);
        
        // Use indexes for filtering
        let channelIds = null;
        
        if (country) {
          const countries = await env.TV_KV.get('index:countries', 'json');
          channelIds = countries[country.toUpperCase()] || [];
        } else if (category) {
          const categories = await env.TV_KV.get('index:categories', 'json');
          channelIds = categories[category.toLowerCase()] || [];
        } else if (language) {
          const languages = await env.TV_KV.get('index:languages', 'json');
          channelIds = languages[language.toLowerCase()] || [];
        }
        
        // Get channels
        let channels;
        if (channelIds) {
          channels = await getChannelsByIds(env, channelIds);
        } else {
          // Return lightweight list for unfiltered
          const light = await env.TV_KV.get('channels:light', 'json');
          const start = (page - 1) * limit;
          channels = light.slice(start, start + limit);
        }
        
        const start = (page - 1) * limit;
        const paged = channels.slice(start, start + limit);
        
        return Response.json({
          page,
          limit,
          total: channels.length,
          channels: paged
        }, { headers });
      }

      // GET /categories
      if (path === '/categories') {
        const categories = await env.TV_KV.get('index:categories', 'json');
        return Response.json(Object.keys(categories).sort(), { headers });
      }

      // GET /countries
      if (path === '/countries') {
        const countries = await env.TV_KV.get('index:countries', 'json');
        return Response.json(Object.keys(countries).sort(), { headers });
      }

      return Response.json({ error: 'Not found' }, { status: 404, headers });

    } catch (e) {
      return Response.json({ error: e.message }, { status: 500, headers });
    }
  }
};

async function findChannel(env, id) {
  // Check lightweight list first
  const light = await env.TV_KV.get('channels:light', 'json');
  const found = light.find(c => c.id.toLowerCase() === id.toLowerCase());
  
  if (!found) return null;
  
  // Get full channel data from chunks
  const meta = await env.TV_KV.get('channels:meta', 'json');
  if (!meta) return found;
  
  for (let i = 0; i < meta.chunks; i++) {
    const chunk = await env.TV_KV.get(`channels:chunk:${i}`, 'json');
    if (chunk) {
      const full = chunk.find(c => c.id === found.id);
      if (full) return full;
    }
  }
  
  return found;
}

async function getChannelsByIds(env, ids) {
  const channels = [];
  const meta = await env.TV_KV.get('channels:meta', 'json');
  if (!meta) return [];
  
  const idSet = new Set(ids.map(id => id.toLowerCase()));
  
  for (let i = 0; i < meta.chunks; i++) {
    const chunk = await env.TV_KV.get(`channels:chunk:${i}`, 'json');
    if (chunk) {
      for (const c of chunk) {
        if (idSet.has(c.id.toLowerCase())) {
          channels.push(c);
        }
      }
    }
  }
  
  return channels;
}
