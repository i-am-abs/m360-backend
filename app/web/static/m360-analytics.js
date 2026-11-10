(function (global) {
  'use strict';

  var MARKS = [25, 50, 75];
  var base = {};
  var visitor = null;
  var token = null;
  var apiHost = null;

  function nextMilestone(prevMark, position, duration) {
    if (!duration || duration <= 0) return null;
    var pct = (position / duration) * 100;
    for (var i = 0; i < MARKS.length; i++) {
      var m = MARKS[i];
      if (m > prevMark && pct >= m) return m;
    }
    return null;
  }

  function uuid() {
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    return 'v-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  }

  function visitorId() {
    if (visitor) return visitor;
    try {
      var key = 'm360_visitor_id';
      var v = global.localStorage.getItem(key);
      if (!v) {
        v = uuid();
        global.localStorage.setItem(key, v);
      }
      visitor = v;
    } catch (e) {
      visitor = uuid();
    }
    return visitor;
  }

  function init(config) {
    token = (config && config.token) || null;
    apiHost = (config && config.apiHost) || 'https://api.mixpanel.com';
    if (!token || typeof global.mixpanel === 'undefined') return;
    try {
      var mp = global.mixpanel;
      mp.init(token, {
        api_host: apiHost,
        persistence: 'localStorage',
        track_pageview: false,
        autotrack: false,
        // Send each event as it happens. With the SDK's default batching,
        // playback/CTA events stay queued and never appear in Live View.
        batch_requests: false,
      });
      base = config.base || {};
      if (!base.anonymous_visitor_id) base.anonymous_visitor_id = visitorId();
      // These are queued by the loader stub and replayed once the SDK loads.
      mp.register(base);
      if (typeof mp.identify === 'function') {
        mp.identify(base.anonymous_visitor_id);
      }
    } catch (e) {}
  }

  // `time` is a Mixpanel-reserved property that sets the event timestamp and
  // must stay numeric epoch seconds. Pair it with a readable, sortable ISO-8601
  // value so the payload is legible without breaking timestamp handling.
  function nowIso() {
    try {
      return new Date().toISOString();
    } catch (e) {
      return '';
    }
  }

  function track(event, props) {
    if (!token) return;
    try {
      // Never cache this: the loader stub is replaced by the real SDK once it
      // loads, so a cached reference would silently swallow later events.
      var mp = global.mixpanel;
      if (!mp || typeof mp.track !== 'function') return;
      mp.track(event, Object.assign({}, props || {}, {
        event_time_iso: nowIso(),
      }));
    } catch (e) {}
  }

  function base64(value) {
    try {
      if (typeof global.btoa === 'function') {
        return global.btoa(unescape(encodeURIComponent(value)));
      }
      if (typeof Buffer !== 'undefined') {
        return Buffer.from(value, 'utf8').toString('base64');
      }
    } catch (e) {}
    return null;
  }

  // Unload-safe delivery: sendBeacon survives the navigation Chrome performs
  // when it follows browser_fallback_url, where a normal XHR would be dropped.
  function beaconTrack(event, props) {
    try {
      if (!token) return false;
      var nav = global.navigator;
      if (!nav || typeof nav.sendBeacon !== 'function') return false;
      var properties = Object.assign({}, base, props || {}, {
        token: token,
        // Reserved: numeric epoch seconds for Mixpanel's event timestamp.
        time: Math.floor(Date.now() / 1000),
        // Readable companion so the event is legible in exports/Live View.
        event_time_iso: nowIso(),
        distinct_id: base.anonymous_visitor_id || visitorId(),
      });
      var encoded = base64(JSON.stringify({ event: event, properties: properties }));
      if (!encoded) return false;
      var host = (apiHost || 'https://api.mixpanel.com').replace(/\/+$/, '');
      var body = 'data=' + encodeURIComponent(encoded);
      if (typeof global.Blob === 'function') {
        return nav.sendBeacon(
          host + '/track',
          new global.Blob([body], { type: 'application/x-www-form-urlencoded' })
        ) === true;
      }
      return nav.sendBeacon(host + '/track', body) === true;
    } catch (e) {
      return false;
    }
  }

  function setupPlayer(video, extra) {
    if (!video) return;
    var baseProps = Object.assign({}, base, extra || {});
    var mark = 0;
    var started = false;

    function fireStarted() {
      if (started) return;
      started = true;
      mark = 0;
      track('video_playback_started', Object.assign({}, baseProps, {
        mux_playback_id: baseProps.mux_playback_id || '',
        video_duration_seconds: video.duration || null,
      }));
    }

    video.addEventListener('playing', fireStarted);

    video.addEventListener('timeupdate', function () {
      if (!started) return;
      var m = nextMilestone(mark, video.currentTime, video.duration);
      if (m === null) return;
      mark = m;
      track('video_playback_' + m + '_percent', Object.assign({}, baseProps, {
        playback_position_seconds: Math.round(video.currentTime),
        playback_percentage: m,
        video_duration_seconds: video.duration || null,
      }));
    });

    video.addEventListener('ended', function () {
      track('video_playback_completed', Object.assign({}, baseProps, {
        playback_position_seconds: Math.round(video.currentTime),
        playback_percentage: 100,
        video_duration_seconds: video.duration || null,
      }));
      started = false;
      mark = 0;
    });

    video.addEventListener('error', function () {
      track('video_playback_error', Object.assign({}, baseProps, {
        error_code: (video.error && video.error.code) || '',
        error_type: 'media_error',
        sanitized_error_message: 'Playback failed',
      }));
    });

    // The embed can autoplay before this script attaches; treat an
    // already-playing video as started so no playback event is lost.
    if (!video.paused && video.currentTime > 0) fireStarted();
  }

  var api = {
    nextMilestone: nextMilestone,
    visitorId: visitorId,
    init: init,
    track: track,
    beaconTrack: beaconTrack,
    setupPlayer: setupPlayer,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.M360Analytics = api;
})(typeof window !== 'undefined' ? window : globalThis);
