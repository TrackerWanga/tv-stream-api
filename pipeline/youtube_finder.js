// Searches YouTube for live streams of channels without IPTV streams
import ytSearch from 'yt-search';
import fs from 'fs';
import path from 'path';

const __dirname = path.dirname(new URL(import.meta.url).pathname);

async function searchYouTube(query) {
  try {
    const results = await ytSearch(query + ' live stream');
    // Filter for live streams
    const live = results.videos.filter(v => 
      v.type === 'live' || v.status === 'LIVE' || v.duration?.toString().includes(':')
    );
    return live.length > 0 ? live[0].url : null;
  } catch (e) {
    return null;
  }
}

async function main() {
  console.log('🔍 YouTube Live Finder');
  console.log('='.repeat(60));

  // Load channels from metadata
  const channelsPath = path.join(__dirname, '..', 'data', 'channels.json');
  if (!fs.existsSync(channelsPath)) {
    console.log('No channels.json found, skipping YouTube search');
    process.exit(0);
  }

  const channels = JSON.parse(fs.readFileSync(channelsPath, 'utf-8'));
  
  // Load existing IPTV streams to avoid duplicate work
  const livePath = path.join(__dirname, '..', 'data', 'streams_live.json');
  let existingIds = new Set();
  if (fs.existsSync(livePath)) {
    const live = JSON.parse(fs.readFileSync(livePath, 'utf-8'));
    existingIds = new Set(Object.keys(live.streams || {}));
  }

  // Filter: popular categories, no existing stream
  const popularCategories = ['sports', 'news', 'entertainment', 'movies', 'music'];
  const toSearch = channels.filter(c => {
    const hasStream = existingIds.has(c.id) || existingIds.has(c.name);
    const isPopular = c.categories?.some(cat => popularCategories.includes(cat));
    return !hasStream && isPopular;
  });

  // Limit to 200 most popular
  const limited = toSearch.slice(0, 200);

  console.log(`Channels to search: ${limited.length} (of ${channels.length} total)`);
  
  const youtubeStreams = {};
  let found = 0;

  for (let i = 0; i < limited.length; i++) {
    const channel = limited[i];
    console.log(`  [${i+1}/${limited.length}] Searching: ${channel.name}...`);
    
    const url = await searchYouTube(channel.name);
    if (url) {
      found++;
      youtubeStreams[channel.id] = {
        id: channel.id,
        name: channel.name,
        url: url,
        logo: channel.logo || '',
        group: channel.categories?.[0] || 'general',
        source: 'youtube',
        status: 'live',
        country: channel.country || '',
        categories: channel.categories || []
      };
      console.log(`    ✅ Found YouTube live: ${url.substring(0, 60)}...`);
    }
    
    // Rate limit: 1 search per second
    if (i < limited.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  // Save
  const outputPath = path.join(__dirname, '..', 'data', 'youtube_streams.json');
  const output = {
    updated: new Date().toISOString(),
    total: found,
    streams: youtubeStreams
  };
  
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));

  console.log(`\n✅ Done! Found ${found} YouTube live streams`);
}

main();
