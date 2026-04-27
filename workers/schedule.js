export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace('/v1', '');
    const params = url.searchParams;
    
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=1800'
    };

    try {
      // GET /schedule?time=now
      if (path === '/schedule' && params.get('time') === 'now') {
        const epgData = await env.TV_KV.get('epg:now', 'json');
        if (!epgData) {
          return Response.json({ 
            message: 'Schedule data not yet synced',
            playing: [] 
          }, { headers });
        }
        return Response.json({
          timestamp: new Date().toISOString(),
          playing: epgData
        }, { headers });
      }

      // GET /channels/:id/schedule
      const scheduleMatch = path.match(/^\/channels\/(.+)\/schedule$/);
      if (scheduleMatch) {
        const channelId = scheduleMatch[1];
        const date = params.get('date') || new Date().toISOString().split('T')[0];
        
        const schedule = await env.TV_KV.get(`epg:${channelId}:${date}`, 'json');
        
        if (!schedule) {
          return Response.json({ 
            channelId,
            date,
            message: 'No schedule available for this date',
            programs: [] 
          }, { headers });
        }
        
        return Response.json({
          channelId,
          date,
          programs: schedule.map(p => ({
            start: p.start,
            end: p.stop,
            title: p.title,
            description: p.desc || '',
            category: p.category || '',
            progress: calculateProgress(p.start, p.stop)
          }))
        }, { headers });
      }

      return Response.json({ error: 'Not found' }, { status: 404, headers });

    } catch (e) {
      return Response.json({ error: e.message }, { status: 500, headers });
    }
  }
};

function calculateProgress(start, stop) {
  const now = Date.now();
  const startTime = new Date(start).getTime();
  const stopTime = new Date(stop).getTime();
  if (now < startTime) return 'upcoming';
  if (now > stopTime) return 'ended';
  return Math.round(((now - startTime) / (stopTime - startTime)) * 100);
}
