const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../web/home-discovery.js'), 'utf8');

async function run(server, failure = false) {
  const requests = [];
  const events = {};
  const queue = [];
  const context = {
    URL, Map,
    location:{hash:'#/', href:'http://localhost:9180/', origin:'http://localhost:9180'},
    localStorage:{getItem:() => JSON.stringify({state:{currentServer:server}})},
    document:{body:{classList:{toggle(){}}},querySelectorAll:()=>[],querySelector:()=>null},
    MutationObserver:class {observe(){} disconnect(){}},
    window:{addEventListener:(name, callback)=>{events[name]=callback;}},
    setTimeout:callback=>{queue.push(callback);return queue.length;},clearTimeout(){},
    async fetch(url, options) {
      requests.push({url:String(url),options});
      return {ok:!failure,json:async()=>[]};
    },
  };
  vm.runInNewContext(source, context);
  await new Promise(resolve=>setImmediate(resolve));
  events.hashchange();
  while (queue.length) queue.shift()();
  return requests;
}

test('genre discovery uses the authenticated same-origin proxy once per session', async () => {
  const requests = await run({id:'local',type:'navidrome',url:'/navidrome',ndCredential:'test-token'});
  assert.equal(requests.length,1);
  assert.equal(new URL(requests[0].url).pathname,'/navidrome/api/genre');
  assert.equal(requests[0].options.headers['x-nd-authorization'],'Bearer test-token');
  assert.equal(requests[0].options.credentials,'same-origin');
  assert.ok(!requests[0].url.includes('test-token'));
});

test('genre discovery keeps credentials away from external or malformed server URLs', async () => {
  for (const url of ['https://external.invalid','http://[broken']) {
    assert.equal((await run({id:'other',type:'navidrome',url,ndCredential:'secret'})).length,0);
  }
});

test('a failed genre request leaves native discovery available without retry loops', async () => {
  const requests = await run({id:'local',type:'navidrome',url:'/navidrome',ndCredential:'test-token'},true);
  assert.equal(requests.length,1);
});
