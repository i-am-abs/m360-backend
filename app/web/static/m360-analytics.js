(function (global) {
  'use strict';

  var MARKS = [25, 50, 75];
  var client = null;
  var base = {};
  var visitor = null;

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
    if (!config || !config.token || typeof global.mixpanel === 'undefined') {
      client = null;
      return;
    }
    try {
      global.mixpanel.init(config.token, {
        api_host: config.apiHost || 'https://api.mixpanel.com',
        persistence: 'localStorage',
        track_pageview: false,
        autotrack: false,
      });
      client = global.mixpanel;
      base = config.base || {};
      if (!base.anonymous_visitor_id) base.anonymous_visitor_id = visitorId();
      client.register(base);
    } catch (e) {
      client = null;
    }
  }

  function track(event, props) {
    if (!client) return;
    try {
      client.track(event, props || {});
    } catch (e) {}
  }

  function setupPlayer(video, extra) {
    if (!video) return;
    var baseProps = Object.assign({}, base, extra || {});
    var mark = 0;
    var started = false;

    video.addEventListener('playing', function () {
      if (started) return;
      started = true;
      mark = 0;
      track('video_playback_started', Object.assign({}, baseProps, {
        mux_playback_id: baseProps.mux_playback_id || '',
        video_duration_seconds: video.duration || null,
      }));
    });

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
  }

  var api = {
    nextMilestone: nextMilestone,
    visitorId: visitorId,
    init: init,
    track: track,
    setupPlayer: setupPlayer,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.M360Analytics = api;
})(typeof window !== 'undefined' ? window : globalThis);
