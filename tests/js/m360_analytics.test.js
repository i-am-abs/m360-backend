const test = require('node:test');
const assert = require('node:assert');
const { nextMilestone } = require('../../app/web/static/m360-analytics.js');

test('returns 25 when crossing the first mark', () => {
  assert.equal(nextMilestone(0, 26, 100), 25);
});

test('skips marks already passed', () => {
  assert.equal(nextMilestone(25, 60, 100), 50);
});

test('returns null below the next mark', () => {
  assert.equal(nextMilestone(25, 30, 100), null);
});

test('returns null when duration is unknown', () => {
  assert.equal(nextMilestone(0, 10, 0), null);
});

const MODULE_PATH = require.resolve('../../app/web/static/m360-analytics.js');

function loadFresh() {
  delete require.cache[MODULE_PATH];
  delete globalThis.M360Analytics;
  return require(MODULE_PATH);
}

function resetGlobals() {
  delete globalThis.M360Analytics;
  delete global.mixpanel;
  delete global.localStorage;
  delete require.cache[MODULE_PATH];
}

function makeStorage(initial) {
  const store = Object.assign({}, initial || {});
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null;
    },
    setItem(key, value) {
      store[key] = String(value);
    },
  };
}

function stubMixpanel() {
  const calls = { init: [], register: [], track: [] };
  global.mixpanel = {
    init(token, options) {
      calls.init.push({ token: token, options: options });
    },
    register(props) {
      calls.register.push(props);
    },
    track(event, props) {
      calls.track.push({ event: event, props: props });
    },
  };
  return calls;
}

function makeVideo(duration) {
  const handlers = new Map();
  return {
    currentTime: 0,
    duration: duration,
    error: null,
    addEventListener(name, handler) {
      if (!handlers.has(name)) handlers.set(name, []);
      handlers.get(name).push(handler);
    },
    emit(name) {
      (handlers.get(name) || []).slice().forEach((handler) => handler());
    },
  };
}

function percentEvents(calls) {
  return calls.track
    .filter((call) => call.event.indexOf('_percent') !== -1)
    .map((call) => call.event);
}

function events(calls, name) {
  return calls.track.filter((call) => call.event === name);
}

test('init does not throw when mixpanel setup fails and leaves tracking disabled', (t) => {
  t.after(resetGlobals);
  let tracked = 0;
  global.mixpanel = {
    init() {
      throw new Error('mixpanel unavailable');
    },
    register() {},
    track() {
      tracked++;
    },
  };

  const analytics = loadFresh();
  assert.doesNotThrow(() => analytics.init({ token: 'tok' }));
  analytics.track('video_playback_started');
  assert.equal(tracked, 0);
});

test('init with empty or missing token resets client so tracking is a no-op', (t) => {
  t.after(resetGlobals);
  [{ token: '' }, {}].forEach((config) => {
    const analytics = loadFresh();
    const calls = stubMixpanel();
    global.localStorage = makeStorage();
    analytics.init({ token: 'tok' });
    analytics.track('before');
    analytics.init(config);
    analytics.track('after');
    assert.deepEqual(
      calls.track.map((call) => call.event),
      ['before']
    );
  });
});

test('init keeps a provided anonymous visitor id', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  const calls = stubMixpanel();
  global.localStorage = makeStorage({ m360_visitor_id: 'stored-id' });
  analytics.init({
    token: 'tok',
    base: { anonymous_visitor_id: 'dev-1', platform: 'android_app' },
  });
  assert.equal(calls.register.length, 1);
  assert.equal(calls.register[0].anonymous_visitor_id, 'dev-1');
  const video = makeVideo(100);
  analytics.setupPlayer(video, {});
  video.emit('playing');
  const started = events(calls, 'video_playback_started');
  assert.equal(started.length, 1);
  assert.equal(started[0].props.anonymous_visitor_id, 'dev-1');
});

test('setupPlayer fires video_playback_started once with duration', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  const calls = stubMixpanel();
  global.localStorage = makeStorage();
  analytics.init({ token: 'tok', base: { content_id: 'c1' } });

  const video = makeVideo(100);
  analytics.setupPlayer(video, { mux_playback_id: 'mux1' });

  video.emit('playing');
  video.emit('playing');

  const started = events(calls, 'video_playback_started');
  assert.equal(started.length, 1);
  assert.equal(started[0].props.video_duration_seconds, 100);
  assert.equal(started[0].props.mux_playback_id, 'mux1');
  assert.equal(started[0].props.content_id, 'c1');
});

test('timeupdate fires each milestone once and ignores repeats', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  const calls = stubMixpanel();
  global.localStorage = makeStorage();
  analytics.init({ token: 'tok' });

  const video = makeVideo(100);
  analytics.setupPlayer(video);
  video.emit('playing');

  [26, 60, 80].forEach((position) => {
    video.currentTime = position;
    video.emit('timeupdate');
  });
  video.emit('timeupdate');
  video.emit('timeupdate');

  assert.deepEqual(percentEvents(calls), [
    'video_playback_25_percent',
    'video_playback_50_percent',
    'video_playback_75_percent',
  ]);
});

test('seeking backwards does not re-fire earlier milestones', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  const calls = stubMixpanel();
  global.localStorage = makeStorage();
  analytics.init({ token: 'tok' });

  const video = makeVideo(100);
  analytics.setupPlayer(video);
  video.emit('playing');

  video.currentTime = 26;
  video.emit('timeupdate');
  video.currentTime = 60;
  video.emit('timeupdate');
  assert.equal(percentEvents(calls).length, 2);

  video.currentTime = 10;
  video.emit('timeupdate');
  video.currentTime = 40;
  video.emit('timeupdate');

  assert.deepEqual(percentEvents(calls), [
    'video_playback_25_percent',
    'video_playback_50_percent',
  ]);
});

test('ended completes playback and a later play re-arms milestones', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  const calls = stubMixpanel();
  global.localStorage = makeStorage();
  analytics.init({ token: 'tok' });

  const video = makeVideo(100);
  analytics.setupPlayer(video);
  video.emit('playing');
  video.currentTime = 26;
  video.emit('timeupdate');

  video.currentTime = 100;
  video.emit('ended');

  const completed = events(calls, 'video_playback_completed');
  assert.equal(completed.length, 1);
  assert.equal(completed[0].props.playback_percentage, 100);

  video.currentTime = 0;
  video.emit('playing');
  video.currentTime = 26;
  video.emit('timeupdate');

  assert.equal(events(calls, 'video_playback_started').length, 2);
  assert.equal(events(calls, 'video_playback_25_percent').length, 2);
});

test('error fires video_playback_error with a sanitized type', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  const calls = stubMixpanel();
  global.localStorage = makeStorage();
  analytics.init({ token: 'tok' });

  const video = makeVideo(100);
  video.error = { code: 2 };
  analytics.setupPlayer(video);
  video.emit('error');

  const errors = events(calls, 'video_playback_error');
  assert.equal(errors.length, 1);
  assert.equal(errors[0].props.error_type, 'media_error');
  assert.equal(errors[0].props.error_code, 2);
  assert.equal(errors[0].props.sanitized_error_message, 'Playback failed');
});

test('visitorId returns the stored visitor id', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  global.localStorage = makeStorage({ m360_visitor_id: 'stored-id' });

  assert.equal(analytics.visitorId(), 'stored-id');
});

test('visitorId falls back when localStorage throws', (t) => {
  t.after(resetGlobals);
  const analytics = loadFresh();
  global.localStorage = {
    getItem() {
      throw new Error('storage denied');
    },
    setItem() {
      throw new Error('storage denied');
    },
  };

  let id;
  assert.doesNotThrow(() => {
    id = analytics.visitorId();
  });
  assert.equal(typeof id, 'string');
  assert.ok(id.length > 0);
});
