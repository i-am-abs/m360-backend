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
